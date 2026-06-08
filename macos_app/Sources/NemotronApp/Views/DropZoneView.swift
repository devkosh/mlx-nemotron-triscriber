import SwiftUI
import UniformTypeIdentifiers

struct DropZoneView: View {
    @EnvironmentObject var serverManager: ServerManager
    @EnvironmentObject var library: LibraryStore
    @State private var isTargeted = false
    @State private var errorMessage: String?

    private let acceptedTypes: [UTType] = [.audio, .movie, .mpeg4Movie, .mp3, .wav, .aiff]

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16)
                .strokeBorder(
                    isTargeted ? Color.accentColor : Color.secondary.opacity(0.4),
                    style: StrokeStyle(lineWidth: 2, dash: [8])
                )
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(isTargeted ? Color.accentColor.opacity(0.08) : Color.clear)
                )

            VStack(spacing: 12) {
                Image(systemName: isTargeted ? "arrow.down.circle.fill" : "waveform.badge.plus")
                    .font(.system(size: 48))
                    .foregroundStyle(isTargeted ? Color.accentColor : Color.secondary)
                    .animation(.spring(response: 0.3), value: isTargeted)

                Text("Drop audio files here")
                    .font(.title3)
                    .foregroundStyle(.primary)

                Text("m4a · mp3 · wav · mp4 · aiff")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if let error = errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.top, 4)
                }
            }
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onDrop(of: acceptedTypes.map(\.identifier), isTargeted: $isTargeted) { providers in
            handleDrop(providers)
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        errorMessage = nil
        var handled = false
        for provider in providers {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, error in
                guard let data = item as? Data,
                      let url = URL(dataRepresentation: data, relativeTo: nil)
                else { return }
                Task { @MainActor in enqueue(url) }
            }
            handled = true
        }
        return handled
    }

    private func enqueue(_ url: URL) {
        // Copy file to managed audios directory
        let audiosDir = LibraryStore.audiosDir
        try? FileManager.default.createDirectory(at: audiosDir, withIntermediateDirectories: true)

        let ext = url.pathExtension
        let id = UUID().uuidString
        let dest = audiosDir.appendingPathComponent("\(id).\(ext)")

        do {
            try FileManager.default.copyItem(at: url, to: dest)
        } catch {
            errorMessage = "Failed to copy file: \(error.localizedDescription)"
            return
        }

        let record = AudioRecord.makeNew(
            originalName: url.lastPathComponent,
            audioPath: dest.path,
            language: AppSettings.defaultLanguage.isEmpty ? nil : AppSettings.defaultLanguage
        )
        library.insert(record)

        let service = TranscribeService(serverManager: serverManager, library: library)
        service.submit(record: record)
    }
}
