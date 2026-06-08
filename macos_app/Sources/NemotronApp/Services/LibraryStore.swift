import Foundation
import GRDB
import Combine

@MainActor
final class LibraryStore: ObservableObject {
    static let shared = LibraryStore()

    @Published var records: [AudioRecord] = []

    private var db: DatabaseQueue!
    private var cancellable: AnyCancellable?

    private init() {
        setupDB()
        loadAll()
    }

    private func setupDB() {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = support.appendingPathComponent("mlx-nemotron")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        let dbURL = dir.appendingPathComponent("library.db")
        db = try! DatabaseQueue(path: dbURL.path)

        try! db.write { db in
            try db.create(table: "audio_records", ifNotExists: true) { t in
                t.column("id", .text).primaryKey()
                t.column("originalName", .text).notNull()
                t.column("audioPath", .text).notNull()
                t.column("transcriptPath", .text)
                t.column("status", .text).notNull()
                t.column("language", .text)
                t.column("createdAt", .datetime).notNull()
                t.column("jobId", .text)
            }
        }
    }

    private func loadAll() {
        records = (try? db.read { db in
            try AudioRecord.order(Column("createdAt").desc).fetchAll(db)
        }) ?? []
    }

    func insert(_ record: AudioRecord) {
        var r = record
        try? db.write { db in try r.insert(db) }
        loadAll()
    }

    func update(_ record: AudioRecord) {
        try? db.write { db in try record.update(db) }
        loadAll()
    }

    func delete(_ record: AudioRecord) {
        try? db.write { db in try record.delete(db) }
        // Delete files from disk
        try? FileManager.default.removeItem(atPath: record.audioPath)
        if let tp = record.transcriptPath { try? FileManager.default.removeItem(atPath: tp) }
        loadAll()
    }

    /// Returns the library directory (~/Library/Application Support/mlx-nemotron/)
    static var libraryDir: URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return support.appendingPathComponent("mlx-nemotron")
    }

    static var audiosDir: URL { libraryDir.appendingPathComponent("audios") }
    static var transcriptsDir: URL { libraryDir.appendingPathComponent("transcripts") }
}
