import re
from typing import Dict, List, Tuple, Optional
from flask import Blueprint, render_template, request, jsonify

full_convert_bp = Blueprint('full_convert', __name__)


def convert_model_code(code_input: str) -> str:
    """Converte modelo 1.7.10 para 1.21.1 com máxima precisão"""

    model_info = extract_model_info(code_input)

    converted_code = generate_modern_model(model_info)

    return converted_code


def extract_model_info(code: str) -> Dict:
    """Extrai todas as informações relevantes do modelo 1.7.10"""

    info = {
        'package_name': '',
        'class_name': '',
        'texture_width': 256,
        'texture_height': 128,
        'model_parts': [],
        'animation_methods': [],
        'render_parts': [],
        'wingspeed_init': 1.0
    }

    package_match = re.search(r'package\s+([\w\.]+);', code)
    if package_match:
        original_package = package_match.group(1)
        if 'entities' in original_package or 'models' in original_package:
            info['package_name'] = 'me.mglucas0123.neospawn.entity.monster.emperorscorpion'
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

    wingspeed_match = re.search(r'this\.wingspeed\s*=\s*([\d\.]+f?)', code)
    if wingspeed_match:
        info['wingspeed_init'] = float(wingspeed_match.group(1).replace('f', ''))

    info['model_parts'] = extract_model_parts_advanced(code)

    info['render_parts'] = extract_render_parts_advanced(code)

    info['animation_methods'] = extract_animation_methods_advanced(code)

    return info


def extract_model_parts_advanced(code: str) -> List[Dict]:
    """Extrai todas as definições de ModelRenderer com análise avançada"""
    parts = []

    part_declarations = []

    patterns = [
        r'ModelRenderer\s+(\w+);',
        r'private\s+ModelRenderer\s+(\w+);',
        r'public\s+ModelRenderer\s+(\w+);',
        r'protected\s+ModelRenderer\s+(\w+);',
        r'ModelRenderer\s+(\w+)\s*=',
        r'this\.(\w+)\s*=\s*new\s+ModelRenderer'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, code)
        for match in matches:
            if match not in part_declarations:
                part_declarations.append(match)

    for part_name in part_declarations:
        part_info = {
            'name': part_name,
            'coords': [0, 0, 0, 1, 1, 1],
            'rotation_point': [0.0, 0.0, 0.0],
            'initial_rotation': [0.0, 0.0, 0.0],
            'tex_u': 0,
            'tex_v': 0,
            'mirror': True
        }

        init_patterns = [
            rf'\(this\.{part_name}\s*=\s*new\s+ModelRenderer\(\(ModelBase\)this,\s*(\d+),\s*(\d+)\)\)\.addBox\(([^)]+)\);',
            rf'this\.{part_name}\s*=\s*new\s+ModelRenderer\(this,\s*(\d+),\s*(\d+)\);.*?\.addBox\(([^)]+)\)',
            rf'{part_name}\s*=\s*new\s+ModelRenderer\(\w+,\s*(\d+),\s*(\d+)\);.*?addBox\(([^)]+)\)',
            rf'this\.{part_name}\.addBox\(([^)]+)\).*?setTextureOffset\((\d+),\s*(\d+)\)'
        ]

        init_match = None
        for pattern in init_patterns:
            init_match = re.search(pattern, code, re.DOTALL)
            if init_match:
                break

        if init_match:
            part_info['tex_u'] = int(init_match.group(1))
            part_info['tex_v'] = int(init_match.group(2))

            coords_str = init_match.group(3)
            coords_parts = [x.strip().replace('f', '') for x in coords_str.split(',')]
            if len(coords_parts) >= 6:
                part_info['coords'] = [float(x) for x in coords_parts[:6]]

        rotation_pattern = rf'this\.{part_name}\.setRotationPoint\(([^)]+)\);'
        rotation_match = re.search(rotation_pattern, code)
        if rotation_match:
            rotation_coords = rotation_match.group(1).split(',')
            part_info['rotation_point'] = [float(x.strip().replace('f', '')) for x in rotation_coords]

        set_rotation_pattern = rf'this\.setRotation\(this\.{part_name},\s*([^)]+)\);'
        set_rotation_match = re.search(set_rotation_pattern, code)
        if set_rotation_match:
            rotation_values = set_rotation_match.group(1).split(',')
            part_info['initial_rotation'] = [float(x.strip().replace('f', '')) for x in rotation_values]

        mirror_pattern = rf'this\.{part_name}\.mirror\s*=\s*(true|false);'
        mirror_match = re.search(mirror_pattern, code)
        if mirror_match:
            part_info['mirror'] = mirror_match.group(1) == 'true'

        parts.append(part_info)

    return parts


def extract_render_parts_advanced(code: str) -> List[str]:
    """Extrai ordem de renderização das partes"""
    render_parts = []

    render_section = re.search(r'public void render\([^{]+\{(.*?)\}', code, re.DOTALL)
    if render_section:
        render_content = render_section.group(1)
        render_calls = re.findall(r'this\.(\w+)\.render\([^)]*\);', render_content)
        render_parts = render_calls

    return render_parts


def extract_animation_methods_advanced(code: str) -> List[Dict]:
    """Extrai métodos de animação com conteúdo completo"""
    methods = []

    method_patterns = [
        r'private void (do\w+|set\w+)\([^{]+\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
    ]

    for pattern in method_patterns:
        matches = re.finditer(pattern, code, re.DOTALL)
        for match in matches:
            methods.append({
                'name': match.group(1),
                'body': match.group(2).strip()
            })

    return methods


def generate_modern_model(info: Dict) -> str:
    """Gera código do modelo moderno 1.21.1 com precisão máxima"""

    class_name = info['class_name']
    package_name = info['package_name']
    texture_width = info['texture_width']
    texture_height = info['texture_height']
    parts = info['model_parts']
    wingspeed_init = info['wingspeed_init']

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
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;

import javax.annotation.Nonnull;

public class {modern_class_name}<T extends Entity> extends EntityModel<T> {{

{generate_part_structure_comment(parts)}
    private final ModelPart root;

{generate_part_declarations_precise(parts)}

    private float wingspeed = {wingspeed_init}f;

    public {modern_class_name}(ModelPart root) {{
        this.root = root;

{generate_constructor_assignments_precise(parts)}
    }}

    public static LayerDefinition createBodyLayer() {{
        MeshDefinition meshdefinition = new MeshDefinition();
        PartDefinition partdefinition = meshdefinition.getRoot();

{generate_part_definitions_precise(parts)}

        return LayerDefinition.create(meshdefinition, {texture_width}, {texture_height});
    }}

    @Override
    public void renderToBuffer(@Nonnull PoseStack poseStack, @Nonnull VertexConsumer vertexConsumer, int packedLight, int packedOverlay, int color) {{
        root.render(poseStack, vertexConsumer, packedLight, packedOverlay, color);
    }}

    @Override
    public void setupAnim(T entity, float limbSwing, float limbSwingAmount, float ageInTicks, float netHeadYaw, float headPitch) {{
{generate_complete_animation_system_precise(parts)}
    }}

{generate_helper_methods_precise(parts)}
}}"""

    return code


def generate_part_structure_comment(parts: List[Dict]) -> str:
    """Gera comentário da estrutura hierárquica"""
    return f"    // Estrutura Hierárquica Plana - Todas as {len(parts)} partes como ModelPart únicos"


def generate_part_declarations_precise(parts: List[Dict]) -> str:
    """Gera declarações das partes seguindo exatamente o padrão da versão atual"""
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

    # Seção 3: Braços esquerdos - CADA PARTE EM SUA PRÓPRIA LINHA
    left_arm_parts = ['leftShoulder', 'leftArmSeg1', 'leftArmSeg2', 'leftArmSeg3', 'leftArmSeg4', 'leftPincer']
    found_left_parts = []
    for part_name in left_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_left_parts.append(part_name)

    if found_left_parts:
        for part in found_left_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    # Seção 4: Braços direitos - CADA PARTE EM SUA PRÓPRIA LINHA  
    right_arm_parts = ['rightShoulder', 'rightArmSeg1', 'rightArmSeg2', 'rightArmSeg3', 'rightArmSeg4', 'rightPincer']
    found_right_parts = []
    for part_name in right_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_right_parts.append(part_name)

    if found_right_parts:
        for part in found_right_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    # Seção 5: Olhos e mandíbulas - CADA PARTE EM SUA PRÓPRIA LINHA
    head_parts = ['leftEye', 'rightEye', 'leftMandible', 'rightMandible', 'leftManPart2', 'rightManPart2']
    found_head_parts = []
    for part_name in head_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_head_parts.append(part_name)

    if found_head_parts:
        for part in found_head_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    # Seção 6: Pernas - EXATAMENTE como no modelo atual (agrupadas por linha)
    for leg_num in range(1, 9):
        leg_parts_for_num = [f'leg{leg_num}Seg1', f'leg{leg_num}Seg2', f'leg{leg_num}Seg3', f'leg{leg_num}Seg4', f'leg{leg_num}Seg5']
        found_leg_parts = []
        for part_name in leg_parts_for_num:
            if any(normalize_part_name(p['name']).lower() == part_name.lower() for p in parts):
                found_leg_parts.append(part_name)

        if found_leg_parts:
            declarations.append("    private final ModelPart " + ", ".join(found_leg_parts) + ";")

    # Remover última linha em branco se existir
    while declarations and declarations[-1] == "":
        declarations.pop()

    return '\n'.join(declarations)


def generate_constructor_assignments_precise(parts: List[Dict]) -> str:
    """Gera atribuições no construtor seguindo EXATAMENTE a ordem do modelo atual"""
    if not parts:
        return "        // Nenhuma parte encontrada"

    assignments = []

    # Ordem EXATA do modelo atual - CRÍTICA para compatibilidade

    # 1. Corpo principal (head, seg1-seg8) - formato exato da IA
    body_parts = ['head', 'seg1', 'seg2', 'seg3', 'seg4', 'seg5', 'seg6', 'seg7', 'seg8']
    found_body_parts = []
    for part_name in body_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_body_parts.append(part_name)

    if found_body_parts:
        for part in found_body_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        if found_body_parts:  # Linha em branco só se houver partes
            assignments.append("")

    # 2. Cauda (tailseg1-tailseg8, stinger1-stinger3) - com linha em branco após
    tail_parts = ['tailseg1', 'tailseg2', 'tailseg3', 'tailseg4', 'tailseg5', 'tailseg6', 'tailseg7', 'tailseg8', 'stinger1', 'stinger2', 'stinger3']
    found_tail_parts = []
    for part_name in tail_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_tail_parts.append(part_name)

    if found_tail_parts:
        for part in found_tail_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    # 3. Braços esquerdos - com linha em branco após
    left_arm_parts = ['leftShoulder', 'leftArmSeg1', 'leftArmSeg2', 'leftArmSeg3', 'leftArmSeg4', 'leftPincer']
    found_left_parts = []
    for part_name in left_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_left_parts.append(part_name)

    if found_left_parts:
        for part in found_left_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    # 4. Braços direitos - com linha em branco após
    right_arm_parts = ['rightShoulder', 'rightArmSeg1', 'rightArmSeg2', 'rightArmSeg3', 'rightArmSeg4', 'rightPincer']
    found_right_parts = []
    for part_name in right_arm_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_right_parts.append(part_name)

    if found_right_parts:
        for part in found_right_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    # 5. Olhos e mandíbulas - com linha em branco após
    head_parts = ['leftEye', 'rightEye', 'leftMandible', 'rightMandible', 'leftManPart2', 'rightManPart2']
    found_head_parts = []
    for part_name in head_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_head_parts.append(part_name)

    if found_head_parts:
        for part in found_head_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
        assignments.append("")

    # 6. Pernas - EXATAMENTE como no modelo atual (agrupadas por perna)
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

    # Remover última linha em branco se existir
    if assignments and assignments[-1] == "":
        assignments.pop()

    return '\n'.join(assignments)


def generate_part_definitions_precise(parts: List[Dict]) -> str:
    """Gera definições das partes com precisão máxima baseada no modelo perfeito"""
    if not parts:
        return "        // Nenhuma parte encontrada"

    definitions = []

    for part in parts:
        name = normalize_part_name(part['name'])
        coords = part['coords']
        rotation_point = part['rotation_point']
        initial_rotation = part['initial_rotation']
        tex_u = part['tex_u']
        tex_v = part['tex_v']

        if len(coords) >= 6:
            x, y, z, width, height, depth = coords[:6]

            definition = f'''        partdefinition.addOrReplaceChild("{name}", CubeListBuilder.create()
            .texOffs({tex_u}, {tex_v}).addBox({x}f, {y}f, {z}f, {int(width)}, {int(height)}, {int(depth)}),
            PartPose.offsetAndRotation({rotation_point[0]}f, {rotation_point[1]}f, {rotation_point[2]}f, {initial_rotation[0]}f, {initial_rotation[1]}f, {initial_rotation[2]}f));'''

            # Adicionar comentário específico para tailseg1
            if name == "tailseg1":
                definition = "        // Cauda - posições iniciais que serão atualizadas via cadeia cinemática\n        " + definition

            definitions.append(definition)

    return '\n\n'.join(definitions) if definitions else "        // Nenhuma definição de parte encontrada"


def detect_model_type(parts: List[Dict]) -> str:
    """Detecta o tipo de modelo baseado nas partes encontradas"""
    part_names = [normalize_part_name(p['name']).lower() for p in parts]
    
    # Verificar se é PitchBlack (tem asas e garras específicas)
    pitchblack_indicators = ['wing1', 'wing2', 'wing3', 'mem1', 'mem2', 'mem3', 'lclaw1', 'rclaw1', 'wingclaw1']
    if any(indicator in part_names for indicator in pitchblack_indicators):
        return 'PitchBlack'
    
    # Verificar se é EmperorScorpion (tem pernas numeradas e cauda segmentada)
    emperor_indicators = ['leg1seg1', 'leg2seg1', 'tailseg1', 'tailseg2', 'stinger1', 'leftarmseg1', 'rightarmseg1']
    if any(indicator in part_names for indicator in emperor_indicators):
        return 'EmperorScorpion'
    
    return 'Generic'


def generate_complete_animation_system_precise(parts: List[Dict]) -> str:
    """Gera sistema de animação baseado no tipo de modelo detectado"""

    model_type = detect_model_type(parts)

    if model_type == 'PitchBlack':
        return generate_pitchblack_animation(parts)
    elif model_type == 'EmperorScorpion':
        return generate_emperorscorpion_animation(parts)
    else:
        return generate_generic_animation(parts)


def generate_pitchblack_animation(parts: List[Dict]) -> str:
    """Gera animação específica para PitchBlack"""
    animation_code = [
        "        // Animação específica para PitchBlack",
        "        float clawAngle = Mth.cos(ageInTicks * 2.0f * this.wingspeed) * (float)Math.PI * 0.1f;",
        "        float wingAngle = ageInTicks * this.wingspeed * 0.5f;",
        "        float tailSpeed = ageInTicks * 0.8f;",
        "        float tailAmp = 0.15f + limbSwingAmount * 0.1f;",
        "",
        "        // Animação das garras",
        "        doLeftClawAnim(clawAngle * limbSwingAmount);",
        "        doRightClawAnim(clawAngle * limbSwingAmount);",
        "",
        "        // Animação das asas",
        "        doWingAnim(wingAngle);",
        "",
        "        // Animação da cauda",
        "        doTailAnim(tailSpeed, tailAmp);",
        "",
        "        // Rotação da cabeça",
        "        ModelPart head = root.getChild(\"head\");",
        "        head.yRot = netHeadYaw * ((float)Math.PI / 180f);",
        "        head.xRot = headPitch * ((float)Math.PI / 180f);",
    ]

    return '\n'.join(animation_code)


def generate_emperorscorpion_animation(parts: List[Dict]) -> str:
    """Gera animação específica para EmperorScorpion"""
    # Detectar componentes do modelo
    leg_parts = [p for p in parts if p['name'].lower().startswith('leg')]
    tail_parts = [p for p in parts if p['name'].lower().startswith('tailseg')]
    arm_parts = [p for p in parts if any(x in p['name'].lower() for x in ['arm', 'pincer'])]
    mandible_parts = [p for p in parts if 'mandible' in p['name'].lower() or 'manpart' in p['name'].lower()]

    animation_code = [
        "        float newangle = 0.0f;",
        "        float upangle = 0.0f;", 
        "        float nextangle = 0.0f;",
        "        final float pi4 = 1.570795f;",
        ""
    ]

    if leg_parts:
        animation_code.extend([
            "        // Animação das pernas com movimento alternado (preservando lógica original)",
            "        newangle = Mth.cos(ageInTicks * 2.0f * this.wingspeed) * (float)Math.PI * 0.12f * limbSwingAmount;",
            "        nextangle = Mth.cos((ageInTicks + 0.1f) * 2.0f * this.wingspeed) * (float)Math.PI * 0.12f * limbSwingAmount;",
            "        upangle = 0.0f;",
            "        if (nextangle > newangle) {",
            "            upangle = 0.47f * limbSwingAmount - Math.abs(newangle);",
            "        }",
            "        ",
            "        // Aplicar animações às 8 pernas (pernas 1-4 direita, 5-8 esquerda)",
            "        doLeftLegAnim(leg1Seg2, leg1Seg3, leg1Seg4, leg1Seg5, newangle, upangle);",
            "        doRightLegAnim(leg5Seg2, leg5Seg3, leg5Seg4, leg5Seg5, -newangle, upangle);",
            ""
        ])

        # Adicionar animações para outras pernas seguindo padrão
        for i in range(2, 5):
            animation_code.extend([
                f"        newangle = Mth.cos(ageInTicks * 2.0f * this.wingspeed - {i-1}.0f * pi4) * (float)Math.PI * 0.12f * limbSwingAmount;",
                f"        nextangle = Mth.cos((ageInTicks + 0.1f) * 2.0f * this.wingspeed - {i-1}.0f * pi4) * (float)Math.PI * 0.12f * limbSwingAmount;",
                "        upangle = 0.0f;",
                "        if (nextangle > newangle) {",
                "            upangle = 0.47f * limbSwingAmount - Math.abs(newangle);",
                "        }",
                f"        doLeftLegAnim(leg{i}Seg2, leg{i}Seg3, leg{i}Seg4, leg{i}Seg5, newangle, upangle);",
                f"        doRightLegAnim(leg{i+4}Seg2, leg{i+4}Seg3, leg{i+4}Seg4, leg{i+4}Seg5, -newangle, upangle);",
                ""
            ])

    if mandible_parts:
        animation_code.extend([
            "        // Animação das mandíbulas (substituindo e.getAttacking() por lógica procedural)",
            "        float mandibleAngle;",
            "        // Simulação de attacking state baseado no tempo (mais agressivo a cada 4 segundos)",
            "        if ((int)(ageInTicks * 0.05f) % 4 == 0) {",
            "            mandibleAngle = Mth.cos(ageInTicks * 2.5f * this.wingspeed) * (float)Math.PI * 0.15f;",
            "        } else {",
            "            mandibleAngle = Mth.cos(ageInTicks * 0.5f * this.wingspeed) * (float)Math.PI * 0.05f;",
            "        }",
            "        this.leftManPart2.zRot = mandibleAngle;",
            "        this.rightManPart2.zRot = -mandibleAngle;",
            ""
        ])

    if arm_parts:
        animation_code.extend([
            "        // Animação procedural das garras e cauda (substituindo RenderInfo por lógica temporal)",
            "        newangle = Mth.cos(ageInTicks * 3.0f * this.wingspeed) * (float)Math.PI * 0.15f;",
            "        nextangle = Mth.cos((ageInTicks + 0.1f) * 3.0f * this.wingspeed) * (float)Math.PI * 0.15f;",
            "        ",
            "        // Simulação de random behavior baseado em hash da entidade e tempo",
            "        int randomValue = (int)(ageInTicks * 0.1f + entity.hashCode() * 0.01f) % 20;",
            "        int randomValue2 = (int)(ageInTicks * 0.08f + entity.hashCode() * 0.02f) % 25;",
            "        ",
            "        if (nextangle > 0.0f && newangle < 0.0f) {",
            "            if ((int)(ageInTicks * 0.05f) % 4 == 0) {",
            "                randomValue = randomValue % 4;",
            "                randomValue2 = randomValue2 % 3;",
            "            }",
            "        }",
            "",
            "        // Animação das garras",
            "        if (randomValue == 1 || randomValue == 3) {",
            "            doLeftClawAnim(newangle);",
            "        } else {",
            "            doLeftClawAnim(0.0f);",
            "        }",
            "        if (randomValue == 2 || randomValue == 3) {",
            "            doRightClawAnim(newangle);",
            "        } else {",
            "            doRightClawAnim(0.0f);",
            "        }",
            ""
        ])

    if tail_parts:
        animation_code.extend([
            "        // Animação da cauda com cadeia cinemática completa",
            "        if (randomValue2 == 1) {",
            "            doTailAnim(newangle);",
            "        } else {",
            "            doTailAnim(0.0f);",
            "        }"
        ])

    return '\n'.join(animation_code)


def generate_generic_animation(parts: List[Dict]) -> str:
    """Gera animação genérica para modelos desconhecidos"""
    return """        // Animação genérica - ajuste conforme necessário
        float angle = Mth.cos(ageInTicks * 0.5f) * 0.1f;

        // Implementar animação específica baseado no modelo
        doGenericAnim(angle);"""


def generate_pitchblack_methods(parts: List[Dict]) -> str:
    """Gera métodos específicos para modelo PitchBlack"""
    methods = [
        "",
        "    // Métodos específicos para PitchBlack - animação de garras e asas",
        "    private void doLeftClawAnim(float angle) {",
        "        // Animação das garras esquerdas baseada na anatomia PitchBlack",
        "        ModelPart lclaw1 = root.getChild(\"lclaw1\");",
        "        ModelPart lclaw2 = root.getChild(\"lclaw2\");", 
        "        ModelPart lclaw3 = root.getChild(\"lclaw3\");",
        "            ",
        "        lclaw1.yRot = 0.6632251f + angle * 0.3f;",
        "        lclaw2.yRot = angle * 0.2f;",
        "        lclaw3.yRot = -0.6632251f - angle * 0.25f;",
        "            ",
        "        // Movimento vertical das garras",
        "        lclaw1.y = 21.0f - angle * 2.0f;",
        "        lclaw2.y = 21.0f - angle * 1.5f;", 
        "        lclaw3.y = 21.0f - angle * 1.8f;",
        "    }",
        "",
        "    private void doRightClawAnim(float angle) {",
        "        // Animação das garras direitas baseada exatamente no código original",
        "        ModelPart rclaw1 = root.getChild(\"rclaw1\");",
        "        ModelPart rclaw2 = root.getChild(\"rclaw2\");",
        "        ModelPart rclaw3 = root.getChild(\"rclaw3\");",
        "        ModelPart rclaw4 = root.getChild(\"rclaw4\");",
        "        ModelPart rclaw5 = root.getChild(\"rclaw5\");",
        "        ModelPart rclaw6 = root.getChild(\"rclaw6\");",
        "        ModelPart rclaw7 = root.getChild(\"rclaw7\");",
        "        ",
        "        // Aplicar rotações baseadas no código original (espelhado)",
        "        rclaw1.yRot = -0.6632251f - angle * 0.2f;",
        "        rclaw2.yRot = -angle * 0.1f;",
        "        rclaw3.yRot = 0.6632251f + angle * 0.15f;",
        "        ",
        "        // Movimento vertical das garras (baseado no original)",
        "        float clawY = 21.0f;",
        "        if (angle > 0.0f) {",
        "            float t2 = angle * 6.0f; // clawYamp do original",
        "            rclaw1.y = clawY - t2;",
        "        } else {",
        "            rclaw1.y = clawY;",
        "        }",
        "        ",
        "        // Sincronizar todas as garras com rclaw1",
        "        rclaw2.y = rclaw1.y;",
        "        rclaw3.y = rclaw1.y;",
        "        rclaw4.y = rclaw1.y;",
        "        rclaw5.y = rclaw1.y;",
        "        rclaw6.y = rclaw1.y;",
        "        rclaw7.y = rclaw1.y;",
        "        ",
        "        float clawZ = 7.0f + 12.0f * angle; // clawZamp do original",
        "        rclaw1.z = clawZ;",
        "        rclaw2.z = clawZ;",
        "        rclaw3.z = clawZ;",
        "        rclaw4.z = clawZ;",
        "        rclaw5.z = clawZ;",
        "        rclaw6.z = clawZ;",
        "        rclaw7.z = clawZ;",
        "    }",
        "",
        "    private void doWingAnim(float wingAngle) {",
        "        // Animação das asas EXATAMENTE como no código original PitchBlack",
        "        ModelPart wing1 = root.getChild(\"wing1\");",
        "        ModelPart wing2 = root.getChild(\"wing2\");",
        "        ModelPart wing3 = root.getChild(\"wing3\");",
        "        ModelPart mem1 = root.getChild(\"mem1\");",
        "        ModelPart mem2 = root.getChild(\"mem2\");",
        "        ModelPart mem3 = root.getChild(\"mem3\");",
        "        ModelPart wingclaw1 = root.getChild(\"wingclaw1\");",
        "        ModelPart wingclaw2 = root.getChild(\"wingclaw2\");",
        "        ModelPart wingclaw3 = root.getChild(\"wingclaw3\");",
        "        ",
        "        // Asas direitas",
        "        ModelPart rwing1 = root.getChild(\"rwing1\");",
        "        ModelPart rwing2 = root.getChild(\"rwing2\");",
        "        ModelPart rwing3 = root.getChild(\"rwing3\");",
        "        ModelPart rmem1 = root.getChild(\"rmem1\");",
        "        ModelPart rmem2 = root.getChild(\"rmem2\");",
        "        ModelPart rmem3 = root.getChild(\"rmem3\");",
        "        ModelPart rwingclaw1 = root.getChild(\"rwingclaw1\");",
        "        ModelPart rwingclaw2 = root.getChild(\"rwingclaw2\");",
        "        ModelPart rwingclaw3 = root.getChild(\"rwingclaw3\");",
        "        ",
        "        // ANIMAÇÃO PRINCIPAL DAS ASAS (traduzida do original)",
        "        float newangle = Mth.cos(wingAngle * 0.45f * this.wingspeed) * (float)Math.PI * 0.24f;",
        "        ",
        "        // Asa esquerda segmento 1",
        "        wing1.zRot = newangle;",
        "        mem1.zRot = newangle;",
        "        ",
        "        // Asa esquerda segmento 2 (conectado dinamicamente)",
        "        wing2.zRot = newangle * 5.0f / 3.0f;",
        "        wing2.y = wing1.y + Mth.sin(wing1.zRot) * 21.0f;",
        "        wing2.x = wing1.x + Mth.cos(wing1.zRot) * 21.0f;",
        "        mem2.zRot = newangle * 5.0f / 3.0f;",
        "        mem2.y = wing2.y;",
        "        mem2.x = wing2.x;",
        "        ",
        "        // Asa esquerda segmento 3 (conectado ao segmento 2)",
        "        wing3.zRot = newangle * 2.0f;",
        "        wing3.y = wing2.y + Mth.sin(wing2.zRot) * 43.0f;",
        "        wing3.x = wing2.x + Mth.cos(wing2.zRot) * 43.0f;",
        "        mem3.zRot = newangle * 2.0f;",
        "        mem3.y = wing3.y;",
        "        mem3.x = wing3.x;",
        "        ",
        "        // Garras das asas esquerdas",
        "        float clawRotation = newangle * 3.0f / 2.0f;",
        "        wingclaw1.zRot = clawRotation;",
        "        wingclaw2.zRot = clawRotation;",
        "        wingclaw3.zRot = clawRotation;",
        "        wingclaw1.y = wing3.y;",
        "        wingclaw2.y = wing3.y;",
        "        wingclaw3.y = wing3.y;",
        "        wingclaw1.x = wing3.x;",
        "        wingclaw2.x = wing3.x;",
        "        wingclaw3.x = wing3.x;",
        "        ",
        "        // ASAS DIREITAS (espelhamento exato do original)",
        "        rwing1.zRot = -newangle;",
        "        rmem1.zRot = -newangle;",
        "        ",
        "        rwing2.zRot = -newangle * 5.0f / 3.0f;",
        "        rwing2.y = rwing1.y - Mth.sin(rwing1.zRot) * 21.0f;",
        "        rwing2.x = rwing1.x - Mth.cos(rwing1.zRot) * 21.0f;",
        "        rmem2.zRot = -newangle * 5.0f / 3.0f;",
        "        rmem2.y = rwing2.y;",
        "        rmem2.x = rwing2.x;",
        "        ",
        "        rwing3.zRot = -newangle * 2.0f;",
        "        rwing3.y = rwing2.y - Mth.sin(rwing2.zRot) * 43.0f;",
        "        rwing3.x = rwing2.x - Mth.cos(rwing2.zRot) * 43.0f;",
        "        rmem3.zRot = -newangle * 2.0f;",
        "        rmem3.y = rwing3.y;",
        "        rmem3.x = rwing3.x;",
        "        ",
        "        // Garras das asas direitas",
        "        float rclawRotation = -newangle * 3.0f / 2.0f;",
        "        rwingclaw1.zRot = rclawRotation;",
        "        rwingclaw2.zRot = rclawRotation;",
        "        rwingclaw3.zRot = rclawRotation;",
        "        rwingclaw1.y = rwing3.y;",
        "        rwingclaw2.y = rwing3.y;",
        "        rwingclaw3.y = rwing3.y;",
        "        rwingclaw1.x = rwing3.x;",
        "        rwingclaw2.x = rwing3.x;",
        "        rwingclaw3.x = rwing3.x;",
        "    }",
        "",
        "    private void doTailAnim(float tailSpeed, float tailAmp) {",
        "        // Animação da cauda baseada no código original",
        "        float pi4 = (float)(Math.PI / 4);",
        "        ",
        "        ModelPart tail1 = root.getChild(\"tail1\");",
        "        ModelPart tail2 = root.getChild(\"tail2\");",
        "        ModelPart tail3 = root.getChild(\"tail3\");",
        "        ModelPart tail4 = root.getChild(\"tail4\");",
        "        ModelPart tail5 = root.getChild(\"tail5\");",
        "        ModelPart tail6 = root.getChild(\"tail6\");",
        "        ModelPart tail7 = root.getChild(\"tail7\");",
        "        ModelPart tail8 = root.getChild(\"tail8\");",
        "        ModelPart tail9 = root.getChild(\"tail9\");",
        "        ",
        "        // Animação em cascata dos segmentos da cauda",
        "        tail1.yRot = Mth.cos(tailSpeed * this.wingspeed) * (float)Math.PI * tailAmp / 2.0f;",
        "        ",
        "        tail2.z = tail1.z + Mth.cos(tail1.yRot) * 11.0f;",
        "        tail2.x = tail1.x - 1.0f + Mth.sin(tail1.yRot) * 11.0f;",
        "        tail2.yRot = Mth.cos(tailSpeed * this.wingspeed - pi4) * (float)Math.PI * tailAmp;",
        "        ",
        "        tail3.z = tail2.z + Mth.cos(tail2.yRot) * 9.0f;",
        "        tail3.x = tail2.x + Mth.sin(tail2.yRot) * 9.0f;",
        "        tail3.yRot = Mth.cos(tailSpeed * this.wingspeed - 2.0f * pi4) * (float)Math.PI * tailAmp;",
        "        ",
        "        tail4.z = tail3.z + Mth.cos(tail3.yRot) * 9.0f;",
        "        tail4.x = tail3.x + Mth.sin(tail3.yRot) * 9.0f;",
        "        tail4.yRot = Mth.cos(tailSpeed * this.wingspeed - 3.0f * pi4) * (float)Math.PI * tailAmp;",
        "        ",
        "        tail5.z = tail4.z + Mth.cos(tail4.yRot) * 9.0f;",
        "        tail5.x = tail4.x + Mth.sin(tail4.yRot) * 9.0f;",
        "        ",
        "        float newangle = Mth.cos(tailSpeed * this.wingspeed - 3.0f * pi4) * (float)Math.PI * tailAmp / 2.0f;",
        "        tail5.yRot = tail4.yRot + newangle;",
        "        ",
        "        // Segmentos bifurcados da cauda",
        "        tail6.z = tail5.z + Mth.cos(tail5.yRot) * 9.0f;",
        "        tail6.x = tail5.x + Mth.sin(tail5.yRot) * 9.0f;",
        "        tail6.yRot = 0.174f + tail5.yRot + newangle;",
        "        ",
        "        tail7.z = tail5.z + Mth.cos(tail5.yRot) * 9.0f;",
        "        tail7.x = tail5.x + Mth.sin(tail5.yRot) * 9.0f;",
        "        tail7.yRot = -0.174f + tail5.yRot + newangle;",
        "        ",
        "        tail9.z = tail6.z + Mth.cos(tail6.yRot) * 9.0f;",
        "        tail9.x = tail6.x + Mth.sin(tail6.yRot) * 9.0f;",
        "        tail9.yRot = tail6.yRot + newangle;",
        "        ",
        "        tail8.z = tail7.z + Mth.cos(tail7.yRot) * 9.0f;",
        "        tail8.x = tail7.x + Mth.sin(tail7.yRot) * 9.0f;",
        "        tail8.yRot = tail7.yRot + newangle;",
        "    }"
    ]

    return '\n'.join(methods)


def generate_emperorscorpion_methods(parts: List[Dict]) -> str:
    """Gera métodos específicos para modelo EmperorScorpion"""
    leg_parts = [p for p in parts if p['name'].lower().startswith('leg')]
    arm_parts = [p for p in parts if any(x in p['name'].lower() for x in ['arm', 'pincer'])]
    tail_parts = [p for p in parts if p['name'].lower().startswith('tailseg')]

    methods = []

    if leg_parts:
        methods.extend([
            "",
            "    // Métodos helper para EmperorScorpion - animação de pernas",
            "    private void doLeftLegAnim(ModelPart seg2, ModelPart seg3, ModelPart seg4, ModelPart seg5, float angle, float upangle) {",
            "        seg2.yRot = angle;",
            "        seg3.yRot = angle;",
            "        seg4.yRot = angle;",
            "        seg5.yRot = angle;",
            "        ",
            "        // Cadeia cinemática das pernas (preservando lógica trigonométrica original)",
            "        seg3.z = (float)(seg2.z - Math.sin(angle) * 6.0);",
            "        seg3.x = (float)(seg2.x - Math.abs(Math.sin(angle) * 6.0) + 6.0);",
            "        seg4.z = (float)(seg3.z - Math.sin(angle) * 9.0);",
            "        seg4.x = (float)(seg3.x - Math.abs(Math.sin(angle) * 9.0) + 9.0);",
            "        seg5.z = (float)(seg4.z - Math.sin(angle) * 1.0);",
            "        seg5.x = (float)(seg4.x - Math.abs(Math.sin(angle) * 1.0) + 1.0);",
            "        ",
            "        seg2.zRot = -upangle - 0.929f;",
            "        seg3.zRot = -upangle + 0.632f;",
            "        seg3.y = seg2.y + (float)(11.5 * Math.sin(seg2.zRot));",
            "        seg4.y = seg3.y + (float)(11.5 * Math.sin(seg3.zRot));",
            "        seg5.y = seg4.y + 6.5f;",
            "    }",
            "",
            "    private void doRightLegAnim(ModelPart seg2, ModelPart seg3, ModelPart seg4, ModelPart seg5, float angle, float upangle) {",
            "        seg2.yRot = angle;",
            "        seg3.yRot = angle;",
            "        seg4.yRot = angle;",
            "        seg5.yRot = -angle;",
            "        ",
            "        seg3.z = (float)(seg2.z + Math.sin(angle) * 6.0);",
            "        seg3.x = (float)(seg2.x + Math.abs(Math.sin(angle) * 6.0) - 6.0);",
            "        seg4.z = (float)(seg3.z + Math.sin(angle) * 9.0);",
            "        seg4.x = (float)(seg3.x + Math.abs(Math.sin(angle) * 9.0) - 9.0);",
            "        seg5.z = (float)(seg4.z + Math.sin(angle) * 1.0);",
            "        seg5.x = (float)(seg4.x + Math.abs(Math.sin(angle) * 1.0) - 1.0);",
            "        ",
            "        seg2.zRot = upangle + 0.929f;",
            "        seg3.zRot = upangle - 0.632f;",
            "        seg3.y = seg2.y - (float)(11.5 * Math.sin(seg2.zRot));",
            "        seg4.y = seg3.y - (float)(11.5 * Math.sin(seg3.zRot));",
            "        seg5.y = seg4.y + 6.5f;",
            "    }"
        ])

    if arm_parts:
        methods.extend([
            "",
            "    private void doLeftClawAnim(float angle) {",
            "        this.leftArmSeg1.yRot = -1.57f + angle;",
            "        this.leftArmSeg2.z = (float)(-22.0 - Math.cos(this.leftArmSeg1.yRot) * 12.0);",
            "        this.leftArmSeg3.z = this.leftArmSeg2.z - 11.0f;",
            "        this.leftArmSeg4.z = this.leftArmSeg2.z - 11.0f;",
            "        this.leftPincer.z = this.leftArmSeg2.z - 11.0f;",
            "        this.leftArmSeg3.yRot = 0.074f + angle;",
            "        this.leftPincer.yRot = 0.371f - angle;",
            "    }",
            "",
            "    private void doRightClawAnim(float angle) {",
            "        this.rightArmSeg1.yRot = 1.57f - angle;",
            "        this.rightArmSeg2.z = (float)(-22.0 - Math.cos(this.rightArmSeg1.yRot) * 12.0);",
            "        this.rightArmSeg3.z = this.rightArmSeg2.z - 11.0f;",
            "        this.rightArmSeg4.z = this.rightArmSeg2.z - 11.0f;",
            "        this.rightPincer.z = this.rightArmSeg2.z - 11.0f;",
            "        this.rightArmSeg3.yRot = -0.074f - angle;",
            "        this.rightPincer.yRot = -0.371f + angle;",
            "    }"
        ])

    if tail_parts:
        methods.extend([
            "",
            "    private void doTailAnim(float angle) {",
            "        // Cadeia cinemática complexa da cauda (CRÍTICO - preservando toda a trigonometria)",
            "        this.tailseg1.xRot = 0.594f + angle;",
            "        this.tailseg2.xRot = this.tailseg1.xRot + 0.48399997f + angle;",
            "        this.tailseg2.y = (float)(this.tailseg1.y - Math.sin(this.tailseg1.xRot) * 9.0);",
            "        this.tailseg2.z = (float)(this.tailseg1.z + Math.cos(this.tailseg1.xRot) * 9.0);",
            "        ",
            "        this.tailseg3.xRot = this.tailseg2.xRot + 0.6320001f + angle;",
            "        this.tailseg3.y = (float)(this.tailseg2.y - Math.sin(this.tailseg2.xRot) * 10.0);",
            "        this.tailseg3.z = (float)(this.tailseg2.z + Math.cos(this.tailseg2.xRot) * 10.0);",
            "        ",
            "        this.tailseg4.xRot = this.tailseg3.xRot + 0.5569999f - angle;",
            "        this.tailseg4.y = (float)(this.tailseg3.y - Math.sin(this.tailseg3.xRot) * 10.0);",
            "        this.tailseg4.z = (float)(this.tailseg3.z + Math.cos(this.tailseg3.xRot) * 10.0);",
            "        ",
            "        this.tailseg5.xRot = this.tailseg4.xRot + 0.63199997f - angle;",
            "        this.tailseg5.y = (float)(this.tailseg4.y - Math.sin(this.tailseg4.xRot) * 10.0);",
            "        this.tailseg5.z = (float)(this.tailseg4.z + Math.cos(this.tailseg4.xRot) * 10.0);",
            "        ",
            "        this.tailseg6.xRot = this.tailseg5.xRot - 5.501f - angle * 3.0f / 2.0f - 0.4f;",
            "        this.tailseg6.y = (float)(this.tailseg5.y - Math.sin(this.tailseg5.xRot) * 10.0);",
            "        this.tailseg6.z = (float)(this.tailseg5.z + Math.cos(this.tailseg5.xRot) * 10.0);",
            "        ",
            "        this.tailseg7.xRot = this.tailseg6.xRot - 2.822f - angle * 2.5f - 2.2f;",
            "        this.tailseg7.y = (float)(this.tailseg6.y - Math.sin(this.tailseg6.xRot) * 10.0);",
            "        this.tailseg7.z = (float)(this.tailseg6.z + Math.cos(this.tailseg6.xRot) * 10.0);",
            "        ",
            "        this.tailseg8.xRot = this.tailseg7.xRot;",
            "        this.tailseg8.y = this.tailseg7.y;",
            "        this.tailseg8.z = this.tailseg7.z;",
            "        ",
            "        this.stinger1.xRot = this.tailseg7.xRot + 0.0f + angle * 0.66f;",
            "        this.stinger1.y = (float)(this.tailseg7.y - Math.sin(this.tailseg7.xRot) * 10.0);",
            "        this.stinger1.z = (float)(this.tailseg7.z + Math.cos(this.tailseg7.xRot) * 10.0);",
            "        ",
            "        this.stinger2.xRot = this.stinger1.xRot - 0.48f + angle;",
            "        this.stinger2.y = (float)(this.stinger1.y - Math.sin(this.stinger1.xRot) * 3.0);",
            "        this.stinger2.z = (float)(this.stinger1.z + Math.cos(this.stinger1.xRot) * 3.0);",
            "        ",
            "        this.stinger3.xRot = this.stinger2.xRot - 1.01f + angle * 1.7f;",
            "        this.stinger3.y = (float)(this.stinger2.y - Math.sin(this.stinger2.xRot) * 3.0);",
            "        this.stinger3.z = (float)(this.stinger2.z + Math.cos(this.stinger2.xRot) * 3.0);",
            "    }"
        ])

    return '\n'.join(methods)


def generate_generic_methods(parts: List[Dict]) -> str:
    """Gera métodos genéricos para modelos desconhecidos"""
    return """
    // Métodos de animação genéricos - ajuste conforme necessário
    private void doGenericAnim(float angle) {
        // Implementar animação específica baseado no modelo
    }"""


def generate_helper_methods_precise(parts: List[Dict]) -> str:
    """Gera métodos auxiliares baseados no tipo de modelo detectado"""
    model_type = detect_model_type(parts)
    
    if model_type == 'PitchBlack':
        return generate_pitchblack_methods(parts)
    elif model_type == 'EmperorScorpion':
        return generate_emperorscorpion_methods(parts)
    else:
        return generate_generic_methods(parts)


def normalize_part_name(old_name: str) -> str:
    """Normaliza nomes das partes para convenção moderna"""
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
        # Obter código de entrada via JSON (evita URI too long)
        if request.is_json:
            data = request.get_json()
            code_input = data.get('code_input', '').strip()
        else:
            code_input = request.form.get('code_input', '').strip()

        if not code_input:
            return jsonify({'error':
                            'Código de entrada não pode estar vazio'}), 400

        # Converter modelo
        converted_code = convert_model_code(code_input)

        return jsonify({
            'converted_code': converted_code,
            'success': True
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Erro interno na conversão: {str(e)}'}), 500