"""Compose the approximate LIMO base with Elephant Robotics' official 280 M5 URDF."""
from __future__ import annotations

import copy
import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def build_robot_description(
    mount_x: float = 0.0,
    mount_y: float = 0.0,
    mount_z: float = 0.205,
    mount_roll: float = 0.0,
    mount_pitch: float = 0.0,
    mount_yaw: float = 0.0,
) -> str:
    """Return a combined URDF XML string.

    The 280 M5 visual/collision meshes are referenced from the installed
    mycobot_description package. Only its link/joint elements are copied;
    the source's xacro property is intentionally not copied into plain URDF.
    """
    own_share = get_package_share_directory("limo_mycobot_control")
    base_path = os.path.join(own_share, "urdf", "limo_mycobot280_base.urdf")
    arm_share = get_package_share_directory("mycobot_description")
    arm_path = os.path.join(
        arm_share, "urdf", "mycobot_280_m5", "mycobot_280_m5.urdf"
    )

    if not os.path.isfile(base_path):
        raise FileNotFoundError(f"Base URDF not found: {base_path}")
    if not os.path.isfile(arm_path):
        raise FileNotFoundError(
            "The official MyCobot 280 M5 URDF was not found at "
            f"{arm_path}. Build/install the Foxy mycobot_description package first."
        )

    base_root = ET.parse(base_path).getroot()
    # Some upstream files declare XML 1.1; normalize that declaration for
    # Python's Expat parser while leaving the actual URDF elements untouched.
    arm_xml = open(arm_path, "r", encoding="utf-8").read()
    arm_xml = arm_xml.replace('<?xml version="1.1"?>', '<?xml version="1.0"?>', 1)
    arm_root = ET.fromstring(arm_xml)
    if _local_name(base_root.tag) != "robot" or _local_name(arm_root.tag) != "robot":
        raise ValueError("Expected <robot> roots in both source descriptions")

    existing_links = {
        item.attrib.get("name")
        for item in base_root
        if _local_name(item.tag) == "link"
    }
    existing_joints = {
        item.attrib.get("name")
        for item in base_root
        if _local_name(item.tag) == "joint"
    }
    manufacturer_joint_limits_deg = {
        "joint2_to_joint1": (-168.0, 168.0),
        "joint3_to_joint2": (-135.0, 135.0),
        "joint4_to_joint3": (-150.0, 150.0),
        "joint5_to_joint4": (-145.0, 145.0),
        "joint6_to_joint5": (-155.0, 160.0),
        "joint6output_to_joint6": (-180.0, 180.0),
    }
    for item in arm_root:
        kind = _local_name(item.tag)
        if kind not in ("link", "joint"):
            continue
        name = item.attrib.get("name")
        if kind == "link" and name in existing_links:
            raise ValueError(f"Duplicate link name in composed URDF: {name}")
        if kind == "joint" and name in existing_joints:
            raise ValueError(f"Duplicate joint name in composed URDF: {name}")
        copied = copy.deepcopy(item)
        # Align the RViz slider bounds with the conservative 280-series API
        # angle limits checked again by the hardware bridge.
        if kind == "joint" and name in manufacturer_joint_limits_deg:
            lower_deg, upper_deg = manufacturer_joint_limits_deg[name]
            limit_element = next(
                (child for child in copied if _local_name(child.tag) == "limit"), None
            )
            if limit_element is not None:
                limit_element.set("lower", f"{lower_deg * 3.141592653589793 / 180.0:.6f}")
                limit_element.set("upper", f"{upper_deg * 3.141592653589793 / 180.0:.6f}")
        base_root.append(copied)

    # Attach the official arm root link to the top plate. This transform is an
    # initial estimate and must be measured on the physical robot before motion.
    mount = ET.SubElement(base_root, "joint", {"name": "arm_mount_fixed", "type": "fixed"})
    ET.SubElement(mount, "parent", {"link": "limo_top_plate"})
    ET.SubElement(mount, "child", {"link": "g_base"})
    ET.SubElement(
        mount,
        "origin",
        {
            "xyz": f"{mount_x:.6f} {mount_y:.6f} {mount_z - 0.196:.6f}",
            "rpy": f"{mount_roll:.6f} {mount_pitch:.6f} {mount_yaw:.6f}",
        },
    )

    # Make the XML easy to inspect when exported to a file.
    try:
        ET.indent(base_root, space="  ")
    except AttributeError:  # Python < 3.9 (not expected on Humble)
        pass
    return ET.tostring(base_root, encoding="unicode")
