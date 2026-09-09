from pathlib import Path

class OpenCVTools:
    """Optional visual-processing helpers. OpenCV is intentionally optional locally."""
    def available(self) -> bool:
        try:
            import cv2  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_thumbnail(self, video_path: str, output_path: str, second: float = 1.0) -> str:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(second * fps))
        ok, frame = cap.read(); cap.release()
        if not ok: raise ValueError("Could not read a frame from the video.")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(output_path, frame): raise ValueError("Could not write thumbnail.")
        return output_path
