import Foundation

struct JobResponse: Decodable {
    let status: String
    let transcript: String?
    let error: String?
}

@MainActor
final class TranscribeService {
    private let serverManager: ServerManager
    private let library: LibraryStore

    init(serverManager: ServerManager, library: LibraryStore) {
        self.serverManager = serverManager
        self.library = library
    }

    func submit(record: AudioRecord) {
        Task { await run(record: record) }
    }

    private func run(record: AudioRecord) async {
        var r = record

        // Ensure audio dir exists
        try? FileManager.default.createDirectory(at: LibraryStore.audiosDir, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(at: LibraryStore.transcriptsDir, withIntermediateDirectories: true)

        // POST /transcribe/path
        let url = serverManager.baseURL.appendingPathComponent("transcribe/path")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        var body: [String: Any] = ["path": r.audioPath, "chunk_seconds": 30]
        if let lang = r.language { body["language"] = lang }
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        guard let (data, _) = try? await URLSession.shared.data(for: req),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let jobId = json["job_id"] as? String
        else {
            r.status = .error
            library.update(r)
            return
        }

        r.jobId = jobId
        r.status = .transcribing
        library.update(r)

        // Poll until done
        await poll(record: &r)
    }

    private func poll(record: inout AudioRecord) async {
        let url = serverManager.baseURL.appendingPathComponent("jobs/\(record.jobId!)")
        for _ in 0..<3600 {  // up to 1h
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard let (data, _) = try? await URLSession.shared.data(from: url),
                  let job = try? JSONDecoder().decode(JobResponse.self, from: data)
            else { continue }

            switch job.status {
            case "done":
                if let text = job.transcript {
                    let transcriptURL = LibraryStore.transcriptsDir.appendingPathComponent("\(record.id).txt")
                    try? text.write(to: transcriptURL, atomically: true, encoding: .utf8)
                    record.transcriptPath = transcriptURL.path
                }
                record.status = .done
                library.update(record)
                return
            case "error":
                record.status = .error
                library.update(record)
                return
            default:
                continue
            }
        }
        record.status = .error
        library.update(record)
    }
}
