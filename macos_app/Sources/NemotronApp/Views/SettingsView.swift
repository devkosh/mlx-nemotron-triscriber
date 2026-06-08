import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var serverManager: ServerManager
    @AppStorage("binaryPath") private var binaryPath = ""
    @AppStorage("defaultLanguage") private var defaultLanguage = ""
    @AppStorage("serverPort") private var serverPort = 9876
    @State private var showFilePicker = false

    var body: some View {
        Form {
            Section("Server") {
                HStack {
                    TextField("Binary path", text: $binaryPath, prompt: Text("auto-detect"))
                        .font(.system(.body, design: .monospaced))
                    Button("Browse…") { showFilePicker = true }
                }

                if let resolved = AppSettings.resolvedBinaryPath {
                    Text("Using: \(resolved)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text("mlx-nemotron not found — install with uv tool install mlx-nemotron-streaming")
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                HStack {
                    Text("Port")
                    Spacer()
                    TextField("Port", value: $serverPort, format: .number)
                        .frame(width: 80)
                        .multilineTextAlignment(.trailing)
                }

                Button("Restart Server") { serverManager.restart() }
                    .buttonStyle(.bordered)
            }

            Section("Transcription") {
                HStack {
                    Text("Default language")
                    Spacer()
                    TextField("auto-detect", text: $defaultLanguage)
                        .frame(width: 120)
                        .multilineTextAlignment(.trailing)
                }
                Text("BCP-47 code, e.g. uk, en-US. Leave blank for auto-detect.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
        .frame(width: 480)
        .fileImporter(isPresented: $showFilePicker, allowedContentTypes: [.unixExecutable, .exe]) { result in
            if let url = try? result.get() { binaryPath = url.path }
        }
    }
}

struct SetupRequiredView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "wrench.and.screwdriver")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("Setup Required")
                .font(.title2.bold())
            Text("mlx-nemotron was not found on your system.\nInstall it, then configure the path in Settings.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Text("uv tool install mlx-nemotron-streaming")
                .font(.system(.body, design: .monospaced))
                .padding(8)
                .background(Color.secondary.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            Button("Open Settings") {
                NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
