import argparse
import json
from engine.video import VideoAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="Run the warehouse behaviour analyzer on one video."
    )
    parser.add_argument("video")
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--output-dir", default="outputs/evaluation")
    args = parser.parse_args()

    incidents, meta = VideoAnalyzer(
        detection_stride=args.stride,
        imgsz=args.imgsz,
        confidence=args.confidence,
    ).analyze(args.video, output_dir=args.output_dir)

    print(
        json.dumps(
            {
                "meta": meta,
                "incident_count": len(incidents),
                "key_findings": meta.get("key_findings", []),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
