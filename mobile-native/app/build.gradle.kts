plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.example.erp.app"
    compileSdk = 37
    defaultConfig {
        // Neutral default; a deployment sets its own ID in its private gradle.properties (erpAppId=...).
        applicationId = providers.gradleProperty("erpAppId").getOrElse("com.example.erp.next")
        minSdk = 28 // Android 9
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    lint {
        abortOnError = true
        warningsAsErrors = true
        // Version nags are handled by the dependency review, not by lint.
        disable += setOf("GradleDependency", "NewerVersionAvailable", "AndroidGradlePluginVersion", "OldTargetApi")
    }
}

dependencies {
    implementation(project(":core"))
    implementation(platform("androidx.compose:compose-bom:2026.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material3:material3-adaptive-navigation-suite")
    implementation("androidx.activity:activity-compose:1.12.4")
    implementation("androidx.biometric:biometric:1.1.0")
    testImplementation("junit:junit:4.13.2")
}
