"""Export the assembled LIMO + MyCobot 280 M5 robot description to a URDF file."""
import argparse
from pathlib import Path

from .description_builder import build_robot_description


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="limo_mycobot280.urdf", help="Output URDF path")
    parser.add_argument("--mount-x", type=float, default=0.0, help="Arm X offset from top plate centre (m)")
    parser.add_argument("--mount-y", type=float, default=0.0, help="Arm Y offset from top plate centre (m)")
    parser.add_argument("--mount-z", type=float, default=0.205, help="Arm base height above floor/odom origin (m)")
    parser.add_argument("--mount-roll", type=float, default=0.0, help="Arm mount roll (rad)")
    parser.add_argument("--mount-pitch", type=float, default=0.0, help="Arm mount pitch (rad)")
    parser.add_argument("--mount-yaw", type=float, default=0.0, help="Arm mount yaw (rad)")
    args = parser.parse_args()

    xml = build_robot_description(
        args.mount_x, args.mount_y, args.mount_z,
        args.mount_roll, args.mount_pitch, args.mount_yaw,
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(xml + "\n", encoding="utf-8")
    print(f"Wrote combined URDF to: {output}")


if __name__ == "__main__":
    main()
