import Foundation
import ImageIO
import Vision

guard CommandLine.arguments.count == 3,
      ["up", "up_mirrored"].contains(CommandLine.arguments[2]) else {
    fputs("expected saved image path and explicit orientation\n", stderr)
    exit(2)
}
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fputs("saved image could not be decoded\n", stderr)
    exit(2)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["en-US"]
request.usesLanguageCorrection = false
do {
    let orientation: CGImagePropertyOrientation = CommandLine.arguments[2] == "up_mirrored" ? .upMirrored : .up
    try VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:]).perform([request])
    let observations = (request.results ?? []).sorted {
        if $0.boundingBox.midY == $1.boundingBox.midY {
            return $0.boundingBox.minX < $1.boundingBox.minX
        }
        return $0.boundingBox.midY > $1.boundingBox.midY
    }
    let lines: [[String: Any]] = observations.compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return ["text": candidate.string, "confidence": Double(candidate.confidence),
                "bounds": ["x": box.minX, "y": box.minY, "width": box.width, "height": box.height]]
    }
    let result: [String: Any] = ["engine": "Apple Vision", "recognition_level": "accurate",
                               "languages": ["en-US"], "language_correction": false, "lines": lines,
                               "request_revision": request.revision, "orientation": CommandLine.arguments[2]]
    let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([10]))
} catch {
    fputs("local Vision recognition failed\n", stderr)
    exit(2)
}
