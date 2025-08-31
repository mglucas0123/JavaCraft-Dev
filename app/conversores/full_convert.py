import re
from typing import Dict, List, Tuple, Optional
from flask import Blueprint, render_template, request, jsonify

full_convert_bp = Blueprint('full_convert', __name__)


def convert_model_code(code_input: str) -> str:
    model_info = extract_model_info(code_input)

    model_info = validate_and_fix_model_info(model_info)

    converted_code = generate_modern_model(model_info)

    return converted_code


def validate_and_fix_model_info(model_info: Dict) -> Dict:
    fixed_parts = []
    for part in model_info.get('model_parts', []):
        coords = part.get('coords', [0, 0, 0, 1, 1, 1])
        if len(coords) < 6:
            coords.extend([1, 1, 1][len(coords)-3:])

        if len(coords) >= 6:
            coords[3] = max(1, abs(coords[3]))
            coords[4] = max(1, abs(coords[4]))
            coords[5] = max(1, abs(coords[5]))

        rotation_point = part.get('rotation_point', [0.0, 0.0, 0.0])
        if len(rotation_point) < 3:
            rotation_point.extend([0.0] * (3 - len(rotation_point)))

        initial_rotation = part.get('initial_rotation', [0.0, 0.0, 0.0])
        if len(initial_rotation) < 3:
            initial_rotation.extend([0.0] * (3 - len(initial_rotation)))

        tex_u = part.get('tex_u', 0)
        tex_v = part.get('tex_v', 0)
        if not isinstance(tex_u, int) or tex_u < 0:
            tex_u = 0
        if not isinstance(tex_v, int) or tex_v < 0:
            tex_v = 0

        fixed_part = {
            'name': part.get('name', 'unknown'),
            'coords': coords,
            'rotation_point': rotation_point,
            'initial_rotation': initial_rotation,
            'tex_u': tex_u,
            'tex_v': tex_v,
            'mirror': part.get('mirror', True)
        }

        fixed_parts.append(fixed_part)

    model_info['model_parts'] = fixed_parts

    if model_info.get('texture_width', 0) <= 0:
        model_info['texture_width'] = 256
    if model_info.get('texture_height', 0) <= 0:
        model_info['texture_height'] = 128

    return model_info


def extract_model_info(code: str) -> Dict:
    info = {
        'package_name': '',
        'class_name': '',
        'texture_width': 256,
        'texture_height': 128,
        'model_parts': [],
        'render_parts': []
    }

    package_match = re.search(r'package\s+([\w\.]+);', code)
    if package_match:
        original_package = package_match.group(1)
        if 'entities' in original_package or 'models' in original_package:
            info['package_name'] = 'me.mglucas0123.neospawn.entity.monster.'
        else:
            info['package_name'] = original_package

    class_match = re.search(r'public\s+class\s+(\w+)\s+extends\s+ModelBase', code)
    if class_match:
        info['class_name'] = class_match.group(1)

    texture_width_match = re.search(r'this\.textureWidth\s*=\s*(\d+)', code)
    if texture_width_match:
        info['texture_width'] = int(texture_width_match.group(1))

    texture_height_match = re.search(r'this\.textureHeight\s*=\s*(\d+)', code)
    if texture_height_match:
        info['texture_height'] = int(texture_height_match.group(1))

    info['model_parts'] = extract_model_parts_advanced(code)

    info['render_parts'] = extract_render_parts_advanced(code)

    info['part_hierarchy'] = extract_part_hierarchy(code)

    return info


def extract_model_parts_advanced(code: str) -> List[Dict]:
    parts = []

    part_declarations = []
    patterns = [
        r'ModelRenderer\s+(\w+);',
        r'private\s+ModelRenderer\s+(\w+);',
        r'public\s+ModelRenderer\s+(\w+);',
        r'protected\s+ModelRenderer\s+(\w+);',
        r'ModelRenderer\s+(\w+)\s*=',
        r'this\.(\w+)\s*=\s*new\s+ModelRenderer',
        r'(\w+)\s*=\s*new\s+ModelRenderer\(',
        r'private\s+final\s+ModelRenderer\s+(\w+);',
        r'public\s+final\s+ModelRenderer\s+(\w+);'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, code)
        for match in matches:
            if match and match.isalnum() and not match.isdigit() and match not in part_declarations:
                part_declarations.append(match)

    unique_declarations = []
    seen = set()
    for part in part_declarations:
        if part not in seen:
            unique_declarations.append(part)
            seen.add(part)

    for part_name in unique_declarations:
        part_info = extract_single_part_info(code, part_name)
        parts.append(part_info)

    return parts


def extract_single_part_info(code: str, part_name: str) -> Dict:
    part_info = {
        'name': part_name,
        'coords': [0, 0, 0, 1, 1, 1],
        'rotation_point': [0.0, 0.0, 0.0],
        'initial_rotation': [0.0, 0.0, 0.0],
        'tex_u': 0,
        'tex_v': 0,
        'mirror': True
    }

    part_block_patterns = [
        rf'(this\.{part_name}\s*=\s*new\s+ModelRenderer[^;]+;[\s\S]*?)(?=this\.\w+\s*=\s*new\s+ModelRenderer|private\s+|public\s+|protected\s+|$)',
        rf'({part_name}\s*=\s*new\s+ModelRenderer[^;]+;[\s\S]*?)(?=\w+\s*=\s*new\s+ModelRenderer|private\s+|public\s+|protected\s+|$)'
    ]

    part_block = ""
    for pattern in part_block_patterns:
        block_match = re.search(pattern, code, re.MULTILINE)
        if block_match:
            part_block = block_match.group(1)
            break

    if not part_block:
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if f'this.{part_name}' in line or f'{part_name} =' in line:
                part_block = '\n'.join(lines[i:i+10])
                break

    tex_patterns = [
        rf'new\s+ModelRenderer\([^,]*,\s*(\d+),\s*(\d+)\)',
        rf'setTextureOffset\((\d+),\s*(\d+)\)',
        rf'setTextureSize\((\d+),\s*(\d+)\)'
    ]

    for pattern in tex_patterns:
        tex_match = re.search(pattern, part_block)
        if tex_match:
            part_info['tex_u'] = int(tex_match.group(1))
            part_info['tex_v'] = int(tex_match.group(2))
            break

    addbox_patterns = [
        rf'{part_name}\.addBox\(([^)]+)\)',
        rf'this\.{part_name}\.addBox\(([^)]+)\)',
        rf'addBox\(([^)]+)\)',
        rf'func_78790_a\(([^)]+)\)',
        rf'addCube\(([^)]+)\)'
    ]

    for pattern in addbox_patterns:
        addbox_match = re.search(pattern, part_block)
        if not addbox_match:
            addbox_match = re.search(pattern, code)

        if addbox_match:
            coords_str = addbox_match.group(1)

            coords_clean = re.sub(r'[fF]', '', coords_str)
            coords_clean = re.sub(r'\s+', ' ', coords_clean)
            coords_parts = [x.strip() for x in coords_clean.split(',')]

            if len(coords_parts) >= 6:
                try:
                    parsed_coords = []
                    for coord in coords_parts[:6]:
                        clean_coord = re.sub(r'[^\d\.\-\+]', '', coord)
                        if clean_coord and clean_coord not in ['-', '+', '.', '']:
                            if '.' in clean_coord:
                                parsed_coords.append(float(clean_coord))
                            else:
                                parsed_coords.append(int(clean_coord))
                        else:
                            parsed_coords.append(0)

                    if len(parsed_coords) == 6:
                        part_info['coords'] = parsed_coords
                        break
                except (ValueError, IndexError):
                    continue

    rotation_patterns = [
        rf'{part_name}\.setRotationPoint\(([^)]+)\)',
        rf'this\.{part_name}\.setRotationPoint\(([^)]+)\)',
        rf'setRotationPoint\({part_name}[^,]*,\s*([^)]+)\)',
        rf'func_78793_a\(([^)]+)\)'
    ]

    for pattern in rotation_patterns:
        rotation_match = re.search(pattern, part_block)
        if not rotation_match:
            rotation_match = re.search(pattern, code)

        if rotation_match:
            rotation_str = rotation_match.group(1)
            rotation_clean = re.sub(r'[fF]', '', rotation_str)
            rotation_parts = [x.strip() for x in rotation_clean.split(',')]

            if len(rotation_parts) >= 3:
                try:
                    parsed_rotation = []
                    for rot in rotation_parts[:3]:
                        clean_rot = re.sub(r'[^\d\.\-\+]', '', rot)
                        if clean_rot and clean_rot not in ['-', '+', '.']:
                            parsed_rotation.append(float(clean_rot))
                        else:
                            parsed_rotation.append(0.0)

                    if len(parsed_rotation) == 3:
                        part_info['rotation_point'] = parsed_rotation
                        break
                except (ValueError, IndexError):
                    continue

    if part_info['rotation_point'] == [0.0, 0.0, 0.0]:
        alt_patterns = [
            rf'{part_name}[^=]*=\s*new\s+ModelRenderer[^;]+;\s*\n[^;]*setRotationPoint\(([^)]+)\)',
            rf'new\s+ModelRenderer[^;]+;\s*{part_name}\.setRotationPoint\(([^)]+)\)'
        ]

        for pattern in alt_patterns:
            alt_match = re.search(pattern, code, re.DOTALL)
            if alt_match:
                rotation_str = alt_match.group(1)
                rotation_clean = re.sub(r'[fF]', '', rotation_str)
                rotation_parts = [x.strip() for x in rotation_clean.split(',')]

                if len(rotation_parts) >= 3:
                    try:
                        parsed_rotation = []
                        for rot in rotation_parts[:3]:
                            clean_rot = re.sub(r'[^\d\.\-\+]', '', rot)
                            if clean_rot and clean_rot not in ['-', '+', '.']:
                                parsed_rotation.append(float(clean_rot))
                            else:
                                parsed_rotation.append(0.0)

                        if len(parsed_rotation) == 3:
                            part_info['rotation_point'] = parsed_rotation
                            break
                    except (ValueError, IndexError):
                        continue

    set_rotation_patterns = [
        rf'setRotation\([^,]*{part_name}[^,]*,\s*([^)]+)\)'
    ]

    for pattern in set_rotation_patterns:
        set_rotation_match = re.search(pattern, code)
        if set_rotation_match:
            rotation_str = set_rotation_match.group(1)
            rotation_clean = re.sub(r'[fF]', '', rotation_str)
            rotation_parts = [x.strip() for x in rotation_clean.split(',')]

            if len(rotation_parts) >= 3:
                try:
                    parsed_rotation = []
                    for rot in rotation_parts[:3]:
                        clean_rot = re.sub(r'[^\d\.\-]', '', rot)
                        if clean_rot:
                            parsed_rotation.append(float(clean_rot))
                        else:
                            parsed_rotation.append(0.0)

                    if len(parsed_rotation) == 3:
                        part_info['initial_rotation'] = parsed_rotation
                except (ValueError, IndexError):
                    pass
            break

    mirror_patterns = [
        rf'{part_name}\.mirror\s*=\s*(true|false)',
        rf'this\.{part_name}\.mirror\s*=\s*(true|false)'
    ]

    for pattern in mirror_patterns:
        mirror_match = re.search(pattern, part_block)
        if mirror_match:
            part_info['mirror'] = mirror_match.group(1) == 'true'
            break

    return part_info


def extract_render_parts_advanced(code: str) -> List[str]:
    render_parts = []

    render_section = re.search(r'public void render\([^{]+\{(.*?)\}', code, re.DOTALL)
    if render_section:
        render_content = render_section.group(1)
        render_calls = re.findall(r'this\.(\w+)\.render\([^)]*\);', render_content)
        render_parts = render_calls

    return render_parts


def extract_part_hierarchy(code: str) -> Dict[str, str]:
    hierarchy = {}

    addchild_patterns = [
        r'this\.(\w+)\.addChild\(this\.(\w+)\);',
        r'(\w+)\.addChild\(this\.(\w+)\);',
        r'this\.(\w+)\.addChild\((\w+)\);',
        r'(\w+)\.addChild\((\w+)\);'
    ]

    for pattern in addchild_patterns:
        matches = re.findall(pattern, code)
        for parent, child in matches:
            parent_normalized = normalize_part_name(parent)
            child_normalized = normalize_part_name(child)
            hierarchy[child_normalized] = parent_normalized

    return hierarchy


def generate_modern_model(info: Dict) -> str:
    class_name = info['class_name']
    package_name = info['package_name']
    texture_width = info['texture_width']
    texture_height = info['texture_height']
    parts = info['model_parts']

    if class_name.startswith('Model'):
        modern_class_name = class_name
    else:
        modern_class_name = class_name + 'Model'

    code = f"""package {package_name};

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.*;
import net.minecraft.world.entity.Entity;

import javax.annotation.Nonnull;

public class {modern_class_name}<T extends Entity> extends EntityModel<T> {{

    private final ModelPart root;

{generate_part_declarations_precise(parts)}

    public {modern_class_name}(ModelPart root) {{
        this.root = root;

{generate_constructor_assignments_precise(parts)}
    }}

    public static LayerDefinition createBodyLayer() {{
        MeshDefinition meshdefinition = new MeshDefinition();
        PartDefinition partdefinition = meshdefinition.getRoot();

{generate_part_definitions_precise(parts, info.get('part_hierarchy', {}))}

        return LayerDefinition.create(meshdefinition, {texture_width}, {texture_height});
    }}

    @Override
    public void renderToBuffer(@Nonnull PoseStack poseStack, @Nonnull VertexConsumer vertexConsumer, int packedLight, int packedOverlay, int color) {{
        root.render(poseStack, vertexConsumer, packedLight, packedOverlay, color);
    }}

    @Override
    public void setupAnim(T entity, float limbSwing, float limbSwingAmount, float ageInTicks, float netHeadYaw, float headPitch) {{}}
}}"""

    return code

def generate_part_declarations_precise(parts: List[Dict]) -> str:
    if not parts:
        return "    // Nenhuma parte encontrada"

    declarations = []

    body_parts = ['head', 'seg1', 'seg2', 'seg3', 'seg4', 'seg5', 'seg6', 'seg7', 'seg8']
    found_body_parts = []
    for part_name in body_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_body_parts.append(part_name)

    if found_body_parts:
        for part in found_body_parts:
            declarations.append(f"    private final ModelPart {part};")
        if found_body_parts:
            declarations.append("")

    tail_parts = ['tailseg1', 'tailseg2', 'tailseg3', 'tailseg4', 'tailseg5', 'tailseg6', 'tailseg7', 'tailseg8', 'stinger1', 'stinger2', 'stinger3']
    found_tail_parts = []
    for part_name in tail_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_tail_parts.append(part_name)

    if found_tail_parts:
        for part in found_tail_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    left_arm_parts = ['leftShoulder', 'leftArmSeg1', 'leftArmSeg2', 'leftArmSeg3', 'leftArmSeg4', 'leftPincer']
    found_left_parts = []
    for part_name in left_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_left_parts.append(part_name)

    if found_left_parts:
        for part in found_left_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    right_arm_parts = ['rightShoulder', 'rightArmSeg1', 'rightArmSeg2', 'rightArmSeg3', 'rightArmSeg4', 'rightPincer']
    found_right_parts = []
    for part_name in right_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_right_parts.append(part_name)

    if found_right_parts:
        for part in found_right_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    head_parts = ['leftEye', 'rightEye', 'leftMandible', 'rightMandible', 'leftManPart2', 'rightManPart2']
    found_head_parts = []
    for part_name in head_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_head_parts.append(part_name)

    if found_head_parts:
        for part in found_head_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    for leg_num in range(1, 9):
        leg_parts_for_num = [f'leg{leg_num}Seg1', f'leg{leg_num}Seg2', f'leg{leg_num}Seg3', f'leg{leg_num}Seg4', f'leg{leg_num}Seg5']
        found_leg_parts = []
        for part_name in leg_parts_for_num:
            if any(normalize_part_name(p['name']).lower() == part_name.lower() for p in parts):
                found_leg_parts.append(part_name)

        if found_leg_parts:
            declarations.append("    private final ModelPart " + ", ".join(found_leg_parts) + ";")

    while declarations and declarations[-1] == "":
        declarations.pop()

    return '\n'.join(declarations)


def generate_constructor_assignments_precise(parts: List[Dict]) -> str:
    if not parts:
        return "        // Nenhuma parte encontrada"

    assignments = []

    body_parts = ['head', 'seg1', 'seg2', 'seg3', 'seg4', 'seg5', 'seg6', 'seg7', 'seg8']
    found_body_parts = []
    for part_name in body_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_body_parts.append(part_name)

    if found_body_parts:
        for part in found_body_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        if found_body_parts:
            assignments.append("")

    tail_parts = ['tailseg1', 'tailseg2', 'tailseg3', 'tailseg4', 'tailseg5', 'tailseg6', 'tailseg7', 'tailseg8', 'stinger1', 'stinger2', 'stinger3']
    found_tail_parts = []
    for part_name in tail_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_tail_parts.append(part_name)

    if found_tail_parts:
        for part in found_tail_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    left_arm_parts = ['leftShoulder', 'leftArmSeg1', 'leftArmSeg2', 'leftArmSeg3', 'leftArmSeg4', 'leftPincer']
    found_left_parts = []
    for part_name in left_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_left_parts.append(part_name)

    if found_left_parts:
        for part in found_left_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    right_arm_parts = ['rightShoulder', 'rightArmSeg1', 'rightArmSeg2', 'rightArmSeg3', 'rightArmSeg4', 'rightPincer']
    found_right_parts = []
    for part_name in right_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_right_parts.append(part_name)

    if found_right_parts:
        for part in found_right_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    head_parts = ['leftEye', 'rightEye', 'leftMandible', 'rightMandible', 'leftManPart2', 'rightManPart2']
    found_head_parts = []
    for part_name in head_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_head_parts.append(part_name)

    if found_head_parts:
        for part in found_head_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    for leg_num in range(1, 9):
        leg_parts_for_num = [f'leg{leg_num}Seg1', f'leg{leg_num}Seg2', f'leg{leg_num}Seg3', f'leg{leg_num}Seg4', f'leg{leg_num}Seg5']
        found_leg_parts = []
        for part_name in leg_parts_for_num:
            if any(normalize_part_name(p['name']).lower() == part_name.lower() for p in parts):
                found_leg_parts.append(part_name)

        if found_leg_parts:
            for part in found_leg_parts:
                assignments.append(f'        this.{part} = root.getChild("{part}");')
            assignments.append("")

    if assignments and assignments[-1] == "":
        assignments.pop()

    return '\n'.join(assignments)


def generate_part_definitions_precise(parts: List[Dict], hierarchy: Dict[str, str] = None) -> str:
    if not parts:
        return "        // Nenhuma parte encontrada"

    if hierarchy is None:
        hierarchy = {}

    definitions = []
    processed_parents = set()

    root_parts = []
    child_parts = []

    for part in parts:
        normalized_name = normalize_part_name(part['name'])
        if normalized_name in hierarchy:
            child_parts.append(part)
        else:
            root_parts.append(part)

    for part in root_parts:
        name = normalize_part_name(part['name'])
        coords = part['coords']
        rotation_point = part['rotation_point']
        initial_rotation = part['initial_rotation']
        tex_u = part['tex_u']
        tex_v = part['tex_v']

        if len(coords) >= 6 and all(isinstance(coord, (int, float)) for coord in coords):
            x, y, z, width, height, depth = coords[:6]

            width = max(1, abs(int(width)))
            height = max(1, abs(int(height)))
            depth = max(1, abs(int(depth)))

            definition = f'''        partdefinition.addOrReplaceChild("{name}", CubeListBuilder.create().texOffs({tex_u}, {tex_v}).addBox({x:.1f}f, {y:.1f}f, {z:.1f}f, {width}, {height}, {depth}), PartPose.offsetAndRotation({rotation_point[0]:.1f}f, {rotation_point[1]:.1f}f, {rotation_point[2]:.1f}f, {initial_rotation[0]:.3f}f, {initial_rotation[1]:.3f}f, {initial_rotation[2]:.3f}f));'''

        definitions.append(definition)

    for part in child_parts:
        name = normalize_part_name(part['name'])
        parent_name = hierarchy[name]
        coords = part['coords']
        rotation_point = part['rotation_point']
        initial_rotation = part['initial_rotation']
        tex_u = part['tex_u']
        tex_v = part['tex_v']

        if len(coords) >= 6 and all(isinstance(coord, (int, float)) for coord in coords):
            x, y, z, width, height, depth = coords[:6]

            width = max(1, abs(int(width)))
            height = max(1, abs(int(height)))
            depth = max(1, abs(int(depth)))

            parent_declaration = ""
            if parent_name not in processed_parents:
                parent_declaration = f"        PartDefinition {parent_name}Def = partdefinition.getChild(\"{parent_name}\");\n        "
                processed_parents.add(parent_name)
            else:
                parent_declaration = "        "

            definition = f'''{parent_declaration}{parent_name}Def.addOrReplaceChild("{name}", CubeListBuilder.create().texOffs({tex_u}, {tex_v}).addBox({x:.1f}f, {y:.1f}f, {z:.1f}f, {width}, {height}, {depth}), PartPose.offsetAndRotation({rotation_point[0]:.1f}f, {rotation_point[1]:.1f}f, {rotation_point[2]:.1f}f, {initial_rotation[0]:.3f}f, {initial_rotation[1]:.3f}f, {initial_rotation[2]:.3f}f));'''

            definitions.append(definition)

    return '\n'.join(definitions) if definitions else "        // Nenhuma definição de parte encontrada"


def normalize_part_name(old_name: str) -> str:
    name_mappings = {
        'lefteye': 'leftEye',
        'righteye': 'rightEye',
        'Lefteye': 'leftEye',
        'Righteye': 'rightEye',
        'LeftEye': 'leftEye',
        'RightEye': 'rightEye',
        'LeftShoulder': 'leftShoulder',
        'RightShoulder': 'rightShoulder',
        'leftShoulder': 'leftShoulder',
        'rightShoulder': 'rightShoulder',
        'LeftArmSeg1': 'leftArmSeg1',
        'LeftArmSeg2': 'leftArmSeg2',
        'LeftArmSeg3': 'leftArmSeg3',
        'LeftArmSeg4': 'leftArmSeg4',
        'RightArmSeg1': 'rightArmSeg1',
        'RightArmSeg2': 'rightArmSeg2',
        'RightArmSeg3': 'rightArmSeg3',
        'RightArmSeg4': 'rightArmSeg4',
        'LeftPincer': 'leftPincer',
        'RightPincer': 'rightPincer',
        'LeftMandible': 'leftMandible',
        'RightMandible': 'rightMandible',
        'LeftManPart2': 'leftManPart2',
        'RightManPart2': 'rightManPart2',
        'Lefteye': 'leftEye',
        'Righteye': 'rightEye',
        'Head': 'head',
        'Seg1': 'seg1',
        'Seg2': 'seg2',
        'Seg3': 'seg3',
        'Seg4': 'seg4',
        'Seg5': 'seg5',
        'Seg6': 'seg6',
        'Seg7': 'seg7',
        'Seg8': 'seg8',
        'Tailseg1': 'tailseg1',
        'Tailseg2': 'tailseg2',
        'Tailseg3': 'tailseg3',
        'Tailseg4': 'tailseg4',
        'Tailseg5': 'tailseg5',
        'Tailseg6': 'tailseg6',
        'Tailseg7': 'tailseg7',
        'Tailseg8': 'tailseg8',
        'Stinger1': 'stinger1',
        'Stinger2': 'stinger2',
        'Stinger3': 'stinger3',
        'Leg1Seg1': 'leg1Seg1',
        'Leg1Seg2': 'leg1Seg2',
        'Leg1Seg3': 'leg1Seg3',
        'Leg1Seg4': 'leg1Seg4',
        'Leg1Seg5': 'leg1Seg5',
        'Leg2Seg1': 'leg2Seg1',
        'Leg2Seg2': 'leg2Seg2',
        'Leg2Seg3': 'leg2Seg3',
        'Leg2Seg4': 'leg2Seg4',
        'Leg2Seg5': 'leg2Seg5',
        'Leg3Seg1': 'leg3Seg1',
        'Leg3Seg2': 'leg3Seg2',
        'Leg3Seg3': 'leg3Seg3',
        'Leg3Seg4': 'leg3Seg4',
        'Leg3Seg5': 'leg3Seg5',
        'Leg4Seg1': 'leg4Seg1',
        'Leg4Seg2': 'leg4Seg2',
        'Leg4Seg3': 'leg4Seg3',
        'Leg4Seg4': 'leg4Seg4',
        'Leg4Seg5': 'leg4Seg5',
        'Leg5Seg1': 'leg5Seg1',
        'Leg5Seg2': 'leg5Seg2',
        'Leg5Seg3': 'leg5Seg3',
        'Leg5Seg4': 'leg5Seg4',
        'Leg5Seg5': 'leg5Seg5',
        'Leg6Seg1': 'leg6Seg1',
        'Leg6Seg2': 'leg6Seg2',
        'Leg6Seg3': 'leg6Seg3',
        'Leg6Seg4': 'leg6Seg4',
        'Leg6Seg5': 'leg6Seg5',
        'Leg7Seg1': 'leg7Seg1',
        'Leg7Seg2': 'leg7Seg2',
        'Leg7Seg3': 'leg7Seg3',
        'Leg7Seg4': 'leg7Seg4',
        'Leg7Seg5': 'leg7Seg5',
        'Leg8Seg1': 'leg8Seg1',
        'Leg8Seg2': 'leg8Seg2',
        'Leg8Seg3': 'leg8Seg3',
        'Leg8Seg4': 'leg8Seg4',
        'Leg8Seg5': 'leg8Seg5',
        'body': 'head',
        'Body': 'head',
        'torso': 'seg1',
        'Torso': 'seg1',
        'segment1': 'seg1',
        'Segment1': 'seg1',
        'segment2': 'seg2',
        'Segment2': 'seg2',
        'segment3': 'seg3',
        'Segment3': 'seg3',
        'segment4': 'seg4',
        'Segment4': 'seg4',
        'segment5': 'seg5',
        'Segment5': 'seg5',
        'segment6': 'seg6',
        'Segment6': 'seg6',
        'segment7': 'seg7',
        'Segment7': 'seg7',
        'segment8': 'seg8',
        'Segment8': 'seg8'
    }

    return name_mappings.get(old_name, old_name)


@full_convert_bp.route('/')
def index():
    return render_template('full_converter.html')


@full_convert_bp.route('/convert', methods=['POST'])
def convert():
    try:
        if request.is_json:
            data = request.get_json()
            code_input = data.get('code_input', '').strip()
        else:
            code_input = request.form.get('code_input', '').strip()

        if not code_input:
            return jsonify({'error':
                           'Código de entrada não pode estar vazio'}), 400

        converted_code = convert_model_code(code_input)

        return jsonify({
            'converted_code': converted_code,
            'success': True
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Erro interno na conversão: {str(e)}'}), 500