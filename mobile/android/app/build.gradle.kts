import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Release signing (MT-5.10-01; parent plan Section 14.3): the keystore
// location and credentials live in `android/key.properties`, which is
// git-ignored (Section 16.2 / 20.4 item 3 — real values never enter
// Git). Nothing secret is hardcoded here or printed by this script;
// `mobile/docs/release-signing.md` documents the setup, rotation and
// backup rules. When the file is absent (fresh clone, CI lint jobs),
// the release build type falls back to the debug key so the project
// still compiles — an installable *release* requires the operator's
// key.properties + keystore, and the signed artifact step then uses
// them.
val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.exists()) {
        keystorePropertiesFile.inputStream().use { load(it) }
    }
}
val hasReleaseKeystore = keystorePropertiesFile.exists()

android {
    namespace = "com.aiagenttaskorchestrator.orchestrator_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11.toString()
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.aiagenttaskorchestrator.orchestrator_mobile"
        // You can update the following values to match your application needs.
        // For more information, see https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // Environment flavors (MT-5.5-02, parent plan Section 14.3): dev and prod
    // install side by side — dev carries an applicationId suffix and its own
    // display name (src/dev/res), prod keeps the base id (src/prod/res).
    // The backend URL is NOT configured here: it reaches Dart through the
    // per-flavor dart-define files under mobile/env/ (see mobile/README.md).
    flavorDimensions.add("environment")
    productFlavors {
        create("dev") {
            dimension = "environment"
            applicationIdSuffix = ".dev"
        }
        create("prod") {
            dimension = "environment"
        }
    }

    signingConfigs {
        if (hasReleaseKeystore) {
            create("release") {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
            }
        }
    }

    buildTypes {
        release {
            // Signed with the outside-Git keystore when key.properties
            // exists (MT-5.10-01); debug-key fallback otherwise so a
            // fresh clone still builds (documented in the signing doc).
            signingConfig = if (hasReleaseKeystore) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

flutter {
    source = "../.."
}
