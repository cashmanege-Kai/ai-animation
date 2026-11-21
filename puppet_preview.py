"""Extract 0–10 seconds of motion and render a procedural wooden puppet."""
import argparse
import json
import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

FPS = 24
SIZE = (540, 960)
WOOD = (89, 156, 210)
CREAM = (170, 213, 231)
GREEN = (55, 90, 57)
DARK = (47, 48, 56)
BROWN = (47, 78, 122)
HAIR = (39, 52, 76)
LIGHT = np.array([-0.45, -0.7, -0.55])


def extract(source, model):
    capture = cv2.VideoCapture(str(source))
    source_fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or source_fps <= 0:
        raise ValueError(f"Cannot read video: {source}")
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.35,
        min_tracking_confidence=0.45,
    )
    poses = []
    background_motion = []
    frame_index = 0
    try:
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
            for i in range(FPS * 10):
                target = round(i * source_fps / FPS)
                while frame_index < target:
                    capture.grab()
                    frame_index += 1
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index += 1
                frame = cv2.resize(frame, (432, 768))
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                result = detector.detect_for_video(image, round(i * 1000 / FPS))
                if result.pose_world_landmarks:
                    points = result.pose_world_landmarks[0]
                    poses.append([[p.x, p.y, p.z, p.visibility] for p in points])
                    hip = result.pose_landmarks[0][23:25]
                    background_motion.append(float(sum(p.x for p in hip) / 2))
                else:
                    poses.append(None)
                    background_motion.append(None)
    finally:
        capture.release()
    return poses, background_motion


def basis(axis):
    axis = axis / max(np.linalg.norm(axis), 1e-7)
    ref = np.array([0., 0., 1.]) if abs(axis[2]) < .85 else np.array([1., 0., 0.])
    side = np.cross(axis, ref)
    side /= max(np.linalg.norm(side), 1e-7)
    return side, np.cross(axis, side)


def ring(center, axis, radius, depth):
    side, forward = basis(axis)
    return [
        center + side * math.cos(a) * r + forward * math.sin(a) * r * depth
        for i in range(12)
        for a in [i * math.tau / 12]
        for r in [radius * (1 if i % 2 == 0 else .93)]
    ]


def tube(mesh, a, b, r1, r2, color, depth=1.):
    axis = b - a
    if np.linalg.norm(axis) < 1e-6:
        return
    near, far = ring(a, axis, r1, depth), ring(b, axis, r2, depth)
    for i in range(12):
        j = (i + 1) % 12
        mesh.append(([near[i], near[j], far[j], far[i]], color))
    mesh.extend([(near[::-1], color), (far, color)])


def joint(mesh, center, width, height, depth, color):
    offset = np.array([0., height, 0.])
    top, bottom = center - offset, center + offset
    tube(mesh, top, center, width * .25, width, color, depth)
    tube(mesh, center, bottom, width, width * .25, color, depth)


def puppet(p):
    mesh = []
    hips = (p[23] + p[24]) / 2
    shoulders = (p[11] + p[12]) / 2
    up = shoulders - hips
    up /= max(np.linalg.norm(up), 1e-7)
    head = shoulders + up * .21
    tube(mesh, hips, shoulders, .125, .18, CREAM, .56)
    tube(mesh, hips + up * .035, hips - up * .245, .135, .218, GREEN, .69)
    tube(mesh, shoulders, head, .043, .047, WOOD)
    joint(mesh, head + up * .021 + np.array([0., 0., .035]), .141, .157, .78, HAIR)
    joint(mesh, head + np.array([0., 0., -.032]), .117, .126, .77, WOOD)
    for x in (-.042, .042):
        joint(mesh, head + np.array([x, -.018, -.12]), .014, .019, .48, DARK)
    joint(mesh, head + np.array([0., .048, -.107]), .024, .006, .5, BROWN)
    for shoulder, elbow, wrist in ((11, 13, 15), (12, 14, 16)):
        tube(mesh, p[shoulder], p[elbow], .056, .04, CREAM)
        tube(mesh, p[elbow], p[wrist], .037, .024, WOOD)
        joint(mesh, p[elbow], .043, .047, 1., WOOD)
        joint(mesh, p[wrist], .034, .051, .65, WOOD)
    for hip, knee, ankle, toe in ((23, 25, 27, 31), (24, 26, 28, 32)):
        tube(mesh, p[hip], p[knee], .071, .046, DARK)
        tube(mesh, p[knee], p[ankle], .046, .029, DARK)
        joint(mesh, p[knee], .049, .049, 1., WOOD)
        tube(mesh, p[ankle], p[toe], .042, .046, BROWN)
    return mesh


def render(poses, translation, path):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)
    if not writer.isOpened():
        raise RuntimeError("Cannot open MP4 encoder")
    previous = None
    gaps = 0
    y = np.linspace(0, 1, SIZE[1])[:, None, None]
    backdrop = np.broadcast_to((np.array([62, 43, 34]) + y * [36, 30, 32]).astype(np.uint8),
                               (SIZE[1], SIZE[0], 3)).copy()
    try:
        for pose, x in zip(poses, translation):
            frame = backdrop.copy()
            if pose is None:
                gaps += 1
            else:
                gaps = 0
                points = np.array(pose)[:, :3]
                previous = points if previous is None else previous * .28 + points * .72
            if previous is not None and gaps <= FPS // 3:
                mesh = puppet(previous)
                offset = np.array([SIZE[0] * (.5 + .35 * ((x or .5) - .5)), SIZE[1] * .48])
                for poly, color in sorted(mesh, key=lambda face: -np.mean(np.array(face[0])[:, 2])):
                    vertices = np.array(poly)
                    normal = np.cross(vertices[1] - vertices[0], vertices[-1] - vertices[0])
                    light = .61 + .37 * abs(np.dot(normal, LIGHT)) / max(np.linalg.norm(normal), 1e-7)
                    shade = tuple(int(c * light) for c in color)
                    projected = np.round(vertices[:, :2] * 380 + offset).astype(np.int32)
                    cv2.fillConvexPoly(frame, projected, shade, cv2.LINE_AA)
            else:
                cv2.putText(frame, "Tracking unavailable", (95, 490), cv2.FONT_HERSHEY_SIMPLEX,
                            .9, (194, 185, 178), 1, cv2.LINE_AA)
            writer.write(frame)
    finally:
        writer.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    poses, translation = extract(args.source, args.model)
    if not any(pose is not None for pose in poses):
        raise RuntimeError("No person tracked in the first 10 seconds")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "motion.json").write_text(json.dumps({
        "fps": FPS, "world_landmarks": poses, "hip_x": translation,
    }, allow_nan=False), encoding="utf-8")
    render(poses, translation, args.output / "puppet-preview.mp4")
    print(f"Tracked {sum(pose is not None for pose in poses)}/{len(poses)} frames.")


if __name__ == "__main__":
    main()

