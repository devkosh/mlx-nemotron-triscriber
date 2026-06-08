import SwiftUI

@main
struct NemotronApp: App {
    @StateObject private var serverManager = ServerManager()
    @StateObject private var library = LibraryStore.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(serverManager)
                .environmentObject(library)
                .frame(minWidth: 800, minHeight: 500)
        }
        .commands {
            CommandGroup(after: .appSettings) {
                Button("Server Status") {}
                    .disabled(true)
                Divider()
            }
        }

        Settings {
            SettingsView()
                .environmentObject(serverManager)
        }
    }
}
