import Foundation
import IOKit

struct LaunchAgentError: LocalizedError {
    let message: String

    var errorDescription: String? {
        message
    }
}

enum LaunchAgentManager {
    static func setEnabled(_ enabled: Bool) throws {
        try runLaunchctl([
            enabled ? "enable" : "disable",
            "gui/\(getuid())/\(appLabel)"
        ])
    }

    private static func runLaunchctl(_ arguments: [String]) throws {
        let process = Process()
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()

        process.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        process.arguments = arguments
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        try process.run()
        process.waitUntilExit()

        guard process.terminationStatus == 0 else {
            let stderr = read(stderrPipe.fileHandleForReading)
            let stdout = read(stdoutPipe.fileHandleForReading)
            throw LaunchAgentError(
                message: "launchctl \(arguments.joined(separator: " ")) failed: \(stderr.isEmpty ? stdout : stderr)"
            )
        }
    }

    private static func read(_ handle: FileHandle) -> String {
        let data = handle.readDataToEndOfFile()
        return String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }
}

enum ClamshellStateReader {
    static func isClosed() -> Bool? {
        let service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPMrootDomain"))
        guard service != 0 else { return nil }
        defer { IOObjectRelease(service) }

        guard let value = IORegistryEntryCreateCFProperty(
            service,
            "AppleClamshellState" as CFString,
            kCFAllocatorDefault,
            0
        )?.takeRetainedValue() else {
            return nil
        }

        if let boolValue = value as? Bool {
            return boolValue
        }

        return (value as? NSNumber)?.boolValue
    }
}
