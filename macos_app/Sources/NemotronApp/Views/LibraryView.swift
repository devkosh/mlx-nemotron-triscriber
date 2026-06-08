import SwiftUI

struct LibraryView: View {
    @EnvironmentObject var serverManager: ServerManager
    @EnvironmentObject var library: LibraryStore
    @Binding var selected: AudioRecord?

    var body: some View {
        List(selection: $selected) {
            if library.records.isEmpty {
                Text("No transcriptions yet")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding()
                    .listRowSeparator(.hidden)
            } else {
                ForEach(library.records) { record in
                    LibraryRowView(record: record)
                        .tag(record)
                        .contextMenu {
                            Button("Delete", role: .destructive) {
                                if selected?.id == record.id { selected = nil }
                                library.delete(record)
                            }
                        }
                }
            }
        }
        .navigationTitle("Library")
        .toolbar {
            ToolbarItem {
                Button {
                    selected = nil
                } label: {
                    Image(systemName: "plus")
                }
                .help("Transcribe new file")
            }
        }
    }
}

struct LibraryRowView: View {
    let record: AudioRecord

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: statusIcon)
                .foregroundStyle(statusColor)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 2) {
                Text(record.originalName)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Text(record.createdAt.formatted(date: .abbreviated, time: .shortened))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    private var statusIcon: String {
        switch record.status {
        case .pending: return "clock"
        case .transcribing: return "waveform"
        case .done: return "checkmark.circle.fill"
        case .error: return "exclamationmark.circle.fill"
        }
    }

    private var statusColor: Color {
        switch record.status {
        case .pending: return .secondary
        case .transcribing: return .accentColor
        case .done: return .green
        case .error: return .red
        }
    }
}
