KOTLIN_TEMPLATES = {
    "basic": {
        "name": "Basic Kotlin Project",
        "structure": {
            "src/main/kotlin": ["Main.kt"],
            "src/test/kotlin": ["MainTest.kt"],
            "gradle/wrapper": ["gradle-wrapper.properties", "gradle-wrapper.jar"],
            "root": ["build.gradle.kts", "settings.gradle.kts", "gradlew", "gradlew.bat"]
        },
        "build_system": "gradle"
    },
    "multiplatform": {
        "name": "Kotlin Multiplatform",
        "structure": {
            "src/commonMain/kotlin": ["Common.kt"],
            "src/jvmMain/kotlin": ["JvmMain.kt"],
            "src/jsMain/kotlin": ["JsMain.kt"],
            "src/nativeMain/kotlin": ["NativeMain.kt"],
            "gradle/wrapper": ["gradle-wrapper.properties", "gradle-wrapper.jar"],
            "root": ["build.gradle.kts", "settings.gradle.kts", "gradlew", "gradlew.bat"]
        },
        "build_system": "gradle"
    },
    "web": {
        "name": "Kotlin Web Project",
        "structure": {
            "src/main/kotlin": ["Application.kt"],
            "src/main/resources/templates": ["index.html"],
            "src/main/resources/static/css": ["styles.css"],
            "src/main/resources/static/js": ["main.js"],
            "gradle/wrapper": ["gradle-wrapper.properties", "gradle-wrapper.jar"],
            "root": ["build.gradle.kts", "settings.gradle.kts", "gradlew", "gradlew.bat"]
        },
        "build_system": "gradle",
        "dependencies": ["ktor", "kotlinx-html"]
    }
} 