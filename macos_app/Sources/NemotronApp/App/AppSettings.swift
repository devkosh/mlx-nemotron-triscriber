import Foundation

enum AppSettings {
    @UserDefault("binaryPath", defaultValue: "") static var binaryPath: String
    @UserDefault("defaultLanguage", defaultValue: "") static var defaultLanguage: String
    @UserDefault("serverPort", defaultValue: 9876) static var serverPort: Int

    static var resolvedBinaryPath: String? {
        let custom = binaryPath
        if !custom.isEmpty && FileManager.default.fileExists(atPath: custom) {
            return custom
        }
        let candidates = [
            "\(NSHomeDirectory())/.local/bin/mlx-nemotron",
            "/usr/local/bin/mlx-nemotron",
            "/opt/homebrew/bin/mlx-nemotron",
        ]
        return candidates.first { FileManager.default.fileExists(atPath: $0) }
    }
}

@propertyWrapper
struct UserDefault<T> {
    let key: String
    let defaultValue: T

    init(_ key: String, defaultValue: T) {
        self.key = key
        self.defaultValue = defaultValue
    }

    var wrappedValue: T {
        get { UserDefaults.standard.object(forKey: key) as? T ?? defaultValue }
        set { UserDefaults.standard.set(newValue, forKey: key) }
    }
}
