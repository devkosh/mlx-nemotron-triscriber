import SwiftUI

struct ContentView: View {
    @EnvironmentObject var serverManager: ServerManager
    @EnvironmentObject var library: LibraryStore
    @State private var selectedRecord: AudioRecord?

    var body: some View {
        Group {
            switch serverManager.state {
            case .notConfigured:
                SetupRequiredView()
            case .starting:
                startingView
            case .failed(let msg):
                failedView(msg)
            case .ready:
                mainView
            }
        }
        .onAppear { serverManager.start() }
    }

    private var mainView: some View {
        NavigationSplitView {
            LibraryView(selected: $selectedRecord)
        } detail: {
            if let record = selectedRecord {
                TranscriptView(record: record)
            } else {
                DropZoneView()
            }
        }
    }

    private var startingView: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Starting transcription server…")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func failedView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundStyle(.orange)
            Text("Server failed to start")
                .font(.headline)
            Text(message)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Retry") { serverManager.restart() }
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
