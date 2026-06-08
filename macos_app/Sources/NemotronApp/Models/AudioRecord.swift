import Foundation
import GRDB

struct AudioRecord: Identifiable, Codable, FetchableRecord, MutablePersistableRecord {
    var id: String
    var originalName: String
    var audioPath: String
    var transcriptPath: String?
    var status: TranscriptionStatus
    var language: String?
    var createdAt: Date
    var jobId: String?

    static let databaseTableName = "audio_records"

    mutating func didInsert(_ inserted: InsertionSuccess) {}
}

enum TranscriptionStatus: String, Codable {
    case pending
    case transcribing
    case done
    case error
}

extension AudioRecord {
    static func makeNew(originalName: String, audioPath: String, language: String?) -> AudioRecord {
        AudioRecord(
            id: UUID().uuidString,
            originalName: originalName,
            audioPath: audioPath,
            transcriptPath: nil,
            status: .pending,
            language: language?.isEmpty == false ? language : nil,
            createdAt: Date(),
            jobId: nil
        )
    }
}
