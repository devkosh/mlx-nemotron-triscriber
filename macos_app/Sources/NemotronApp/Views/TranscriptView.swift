import SwiftUI

struct TranscriptView: View {
    let record: AudioRecord
    @State private var showExportPanel = false

    private var transcript: String? {
        guard let path = record.transcriptPath else { return nil }
        return try? String(contentsOfFile: path, encoding: .utf8)
    }

    var body: some View {
        Group {
            switch record.status {
            case .transcribing, .pending:
                inProgressView

            case .error:
                errorView

            case .done:
                if let text = transcript {
                    transcriptTextView(text)
                } else {
                    Text("Transcript file not found.")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .navigationTitle(record.originalName)
        .navigationSubtitle(record.createdAt.formatted(date: .abbreviated, time: .shortened))
    }

    private var inProgressView: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text(record.status == .transcribing ? "Transcribing…" : "Waiting in queue…")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var errorView: some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundStyle(.orange)
            Text("Transcription failed")
                .font(.headline)
            Text("Check that the server is running and the file is a valid audio format.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func transcriptTextView(_ text: String) -> some View {
        ScrollView {
            Text(text)
                .font(.body)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
        }
        .toolbar {
            ToolbarItemGroup {
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                } label: {
                    Label("Copy", systemImage: "doc.on.doc")
                }
                .help("Copy transcript to clipboard")

                Button {
                    showExportPanel = true
                } label: {
                    Label("Export", systemImage: "square.and.arrow.up")
                }
                .help("Save transcript as text file")
            }
        }
        .fileExporter(
            isPresented: $showExportPanel,
            document: TranscriptDocument(text: text),
            contentType: .plainText,
            defaultFilename: record.originalName.replacingOccurrences(of: ".", with: "_") + "_transcript"
        ) { _ in }
    }
}

struct TranscriptDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.plainText] }
    var text: String

    init(text: String) { self.text = text }
    init(configuration: ReadConfiguration) throws {
        text = String(data: configuration.file.regularFileContents ?? Data(), encoding: .utf8) ?? ""
    }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: (text.data(using: .utf8) ?? Data()))
    }
}
