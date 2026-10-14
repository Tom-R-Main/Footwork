import AVFoundation

// Inspection only: this helper never requests camera authorization.
let status = AVCaptureDevice.authorizationStatus(for: .video)
switch status {
case .authorized: print("authorized")
case .denied: print("denied")
case .restricted: print("restricted")
case .notDetermined: print("not_determined")
@unknown default: print("unknown")
}
