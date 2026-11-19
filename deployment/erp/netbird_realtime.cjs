"use strict";
// Frappe 16 realtime adapter. Forward verified ingress context; never bypass auth.
const { AsyncLocalStorage } = require("node:async_hooks");
const Module = require("node:module");
const http = require("node:http");
const { Readable } = require("node:stream");
const context = new AsyncLocalStorage();
const originalLoad = Module._load;
const originalFetch = globalThis.fetch;
const wrappers = new WeakMap();
const upstream = new URL(process.env.NETBIRD_AUTH_REALTIME_BACKEND_ORIGIN);
const publicHost = process.env.NETBIRD_AUTH_PUBLIC_HOST;
if (upstream.protocol !== "http:" || !publicHost || !/^[a-z0-9.-]+$/.test(publicHost)) {
  throw new Error("Invalid private realtime adapter configuration");
}

globalThis.fetch = function (input, options = {}) {
  const requestContext = context.getStore();
  const url = new URL(typeof input === "string" || input instanceof URL ? input : input.url);
  if (requestContext && url.origin === upstream.origin && url.pathname.startsWith("/api/")) {
    const headers = new Headers(input instanceof Request ? input.headers : undefined);
    new Headers(options.headers).forEach((value, name) => headers.set(name, value));
    headers.set("X-NetBird-User", requestContext.user);
    headers.set("X-NetBird-Frappe-Proof", requestContext.proof);
    headers.set("Host", publicHost);
    headers.set("X-Forwarded-Proto", "https");
    // Node fetch ignores custom Host; use HTTP for these internal GET callbacks.
    const method = (options.method || (input instanceof Request && input.method) || "GET").toUpperCase();
    if (!["GET", "HEAD"].includes(method) || options.body != null) throw new Error("Unsupported realtime backend method");
    headers.set("Accept-Encoding", "identity");
    return new Promise((resolve, reject) => {
      const request = http.request(url, { method, headers: Object.fromEntries(headers), signal: options.signal }, (response) => {
        if (response.statusCode >= 300 && response.statusCode < 400) {
          response.resume(); reject(new Error("Realtime backend redirect denied")); return;
        }
        const responseHeaders = new Headers();
        for (let i = 0; i < response.rawHeaders.length; i += 2) responseHeaders.append(response.rawHeaders[i], response.rawHeaders[i + 1]);
        const noBody = method === "HEAD" || [204, 304].includes(response.statusCode);
        resolve(new Response(noBody ? null : Readable.toWeb(response), {
          status: response.statusCode, statusText: response.statusMessage, headers: responseHeaders,
        }));
      });
      request.setTimeout(15000, () => request.destroy(new Error("Realtime backend timed out")));
      request.on("error", reject);
      request.end();
    });
  }
  return originalFetch(input, options);
};

Module._load = function (request, parent, isMain) {
  const exported = originalLoad.call(this, request, parent, isMain);
  if (typeof request !== "string" || !request.includes("authenticate")) return exported;
  const filename = Module._resolveFilename(request, parent, isMain).replaceAll("\\", "/");
  if (!filename.endsWith("/frappe/realtime/middlewares/authenticate.js")) return exported;
  if (typeof exported !== "function") throw new Error("Unsupported Frappe realtime middleware contract");
  if (wrappers.has(exported)) return wrappers.get(exported);
  function authenticate(socket, next) {
    const headers = socket.request.headers;
    const user = headers["x-netbird-user"];
    const proof = headers["x-netbird-frappe-proof"];
    const identity = typeof user === "string" && typeof proof === "string" && user && proof
      ? Object.freeze({ user, proof }) : undefined;
    return context.run(identity, () => {
      const result = exported(socket, next);
      // Frappe creates this callback synchronously. Bind later permission checks
      // too, even when subsequent Socket.IO events run in another async context.
      if (typeof socket.frappe_request === "function") {
        const call = socket.frappe_request;
        socket.frappe_request = function (...args) {
          return context.run(identity, () => call.apply(this, args));
        };
      }
      return result;
    });
  }
  wrappers.set(exported, authenticate);
  return authenticate;
};
