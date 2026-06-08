import Foundation
import Combine

enum ServerState {
    case notConfigured
    case starting
    case ready
    case failed(String)
}

@MainActor
final class ServerManager: ObservableObject {
    @Published var state: ServerState = .starting

    private var process: Process?
    private var pollTask: Task<Void, Never>?

    var baseURL: URL {
        URL(string: "http://127.0.0.1:\(AppSettings.serverPort)")!
    }

    func start() {
        guard let binary = AppSettings.resolvedBinaryPath else {
            state = .notConfigured
            return
        }
        state = .starting
        spawnProcess(binary: binary)
        pollTask = Task { await pollHealth() }
    }

    func restart() {
        stop()
        start()
    }

    func stop() {
        pollTask?.cancel()
        process?.terminate()
        process = nil
    }

    private func spawnProcess(binary: String) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: binary)
        p.arguments = ["serve", "--port", "\(AppSettings.serverPort)"]
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        p.terminationHandler = { [weak self] _ in
            Task { @MainActor [weak self] in
                if case .ready = self?.state { return }
                self?.state = .failed("Server process exited unexpectedly")
            }
        }
        try? p.run()
        process = p
    }

    private func pollHealth() async {
        let url = baseURL.appendingPathComponent("health")
        for _ in 0..<60 {  // 30s timeout
            try? await Task.sleep(nanoseconds: 500_000_000)
            guard !Task.isCancelled else { return }
            if let _ = try? await URLSession.shared.data(from: url) {
                state = .ready
                return
            }
        }
        state = .failed("Server did not start within 30s")
    }

    deinit {
        process?.terminate()
    }
}
