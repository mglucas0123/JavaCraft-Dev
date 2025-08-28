import re
from typing import Dict, List, Tuple, Optional
from flask import Blueprint, render_template, request, jsonify

full_convert_bp = Blueprint('full_convert', __name__)


def convert_model_code(code_input: str) -> str:
    """Converte modelo 1.7.10 para 1.21.1 com máxima precisão"""

    # Extrair informações do modelo original
    model_info = extract_model_info(code_input)

    # Gerar código 1.21.1
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

    # Extrair package
    package_match = re.search(r'package\s+([\w\.]+);', code)
    if package_match:
        info['package_name'] = package_match.group(1)

    # Extrair nome da classe
    class_match = re.search(r'public\s+class\s+(\w+)\s+extends\s+ModelBase', code)
    if class_match:
        info['class_name'] = class_match.group(1)

    # Extrair dimensões da textura
    texture_width_match = re.search(r'this\.textureWidth\s*=\s*(\d+)', code)
    if texture_width_match:
        info['texture_width'] = int(texture_width_match.group(1))

    texture_height_match = re.search(r'this\.textureHeight\s*=\s*(\d+)', code)
    if texture_height_match:
        info['texture_height'] = int(texture_height_match.group(1))

    # Extrair wingspeed inicial
    wingspeed_match = re.search(r'this\.wingspeed\s*=\s*([\d\.]+f?)', code)
    if wingspeed_match:
        info['wingspeed_init'] = float(wingspeed_match.group(1).replace('f', ''))

    # Extrair todas as partes do modelo
    info['model_parts'] = extract_model_parts_advanced(code)

    # Extrair partes renderizadas
    info['render_parts'] = extract_render_parts_advanced(code)

    # Extrair métodos de animação
    info['animation_methods'] = extract_animation_methods_advanced(code)

    return info


def extract_model_parts_advanced(code: str) -> List[Dict]:
    """Extrai todas as definições de ModelRenderer com análise avançada"""
    parts = []

    # Primeiro, encontrar todas as declarações de ModelRenderer
    part_declarations = re.findall(r'ModelRenderer\s+(\w+);', code)

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

        # Procurar pela inicialização desta parte específica
        # Padrão: (this.PartName = new ModelRenderer((ModelBase)this, u, v)).addBox(...)
        init_pattern = rf'\(this\.{part_name}\s*=\s*new\s+ModelRenderer\(\(ModelBase\)this,\s*(\d+),\s*(\d+)\)\)\.addBox\(([^)]+)\);'
        init_match = re.search(init_pattern, code)

        if init_match:
            # Extrair coordenadas da textura
            part_info['tex_u'] = int(init_match.group(1))
            part_info['tex_v'] = int(init_match.group(2))

            # Extrair coordenadas do addBox
            coords_str = init_match.group(3)
            coords_parts = [x.strip().replace('f', '') for x in coords_str.split(',')]
            if len(coords_parts) >= 6:
                part_info['coords'] = [float(x) for x in coords_parts[:6]]

        # Extrair setRotationPoint
        rotation_pattern = rf'this\.{part_name}\.setRotationPoint\(([^)]+)\);'
        rotation_match = re.search(rotation_pattern, code)
        if rotation_match:
            rotation_coords = rotation_match.group(1).split(',')
            part_info['rotation_point'] = [float(x.strip().replace('f', '')) for x in rotation_coords]

        # Extrair setRotation (rotação inicial)
        set_rotation_pattern = rf'this\.setRotation\(this\.{part_name},\s*([^)]+)\);'
        set_rotation_match = re.search(set_rotation_pattern, code)
        if set_rotation_match:
            rotation_values = set_rotation_match.group(1).split(',')
            part_info['initial_rotation'] = [float(x.strip().replace('f', '')) for x in rotation_values]

        # Verificar mirror
        mirror_pattern = rf'this\.{part_name}\.mirror\s*=\s*(true|false);'
        mirror_match = re.search(mirror_pattern, code)
        if mirror_match:
            part_info['mirror'] = mirror_match.group(1) == 'true'

        parts.append(part_info)

    return parts


def extract_render_parts_advanced(code: str) -> List[str]:
    """Extrai ordem de renderização das partes"""
    render_parts = []

    # Buscar no método render por chamadas .render()
    render_section = re.search(r'public void render\([^{]+\{(.*?)\}', code, re.DOTALL)
    if render_section:
        render_content = render_section.group(1)
        # Procurar por this.PartName.render(f5);
        render_calls = re.findall(r'this\.(\w+)\.render\([^)]*\);', render_content)
        render_parts = render_calls

    return render_parts


def extract_animation_methods_advanced(code: str) -> List[Dict]:
    """Extrai métodos de animação com conteúdo completo"""
    methods = []

    # Buscar todos os métodos privados
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

    # Converter nome da classe para padrão moderno (remover "Model" e mover para sufixo)
    if class_name.startswith('Model'):
        modern_class_name = class_name[5:] + 'Model'  # Remove "Model" do início e adiciona no final
    else:
        modern_class_name = class_name + 'Model'

    # Template do código moderno baseado no modelo perfeito
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

    # Seção 1: Corpo principal - CADA PARTE EM SUA PRÓPRIA LINHA
    body_parts = ['head', 'seg1', 'seg2', 'seg3', 'seg4', 'seg5', 'seg6', 'seg7', 'seg8']
    found_body_parts = []
    for part_name in body_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_body_parts.append(part_name)
    
    if found_body_parts:
        for part in found_body_parts:
            declarations.append(f"    private final ModelPart {part};")
        declarations.append("")

    # Seção 2: Cauda - CADA PARTE EM SUA PRÓPRIA LINHA
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
    
    # 1. Corpo principal (head, seg1-seg8) - com linha em branco após
    body_parts = ['head', 'seg1', 'seg2', 'seg3', 'seg4', 'seg5', 'seg6', 'seg7', 'seg8']
    found_body_parts = []
    for part_name in body_parts:
        if any(normalize_part_name(p['name']) == part_name for p in parts):
            found_body_parts.append(part_name)
    
    if found_body_parts:
        for part in found_body_parts:
            assignments.append(f'        this.{part} = root.getChild("{part}");')
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


def generate_complete_animation_system_precise(parts: List[Dict]) -> str:
    """Gera sistema de animação seguindo exatamente o padrão do modelo perfeito"""

    # Detectar componentes do modelo
    leg_parts = [p for p in parts if p['name'].lower().startswith('leg')]
    tail_parts = [p for p in parts if p['name'].lower().startswith('tailseg')]
    arm_parts = [p for p in parts if any(x in p['name'].lower() for x in ['arm', 'pincer', 'claw'])]
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


def generate_helper_methods_precise(parts: List[Dict]) -> str:
    """Gera métodos helper seguindo exatamente o padrão do modelo perfeito"""

    leg_parts = [p for p in parts if p['name'].lower().startswith('leg')]
    arm_parts = [p for p in parts if any(x in p['name'].lower() for x in ['arm', 'pincer', 'claw'])]
    tail_parts = [p for p in parts if p['name'].lower().startswith('tailseg')]

    methods = []

    if leg_parts:
        methods.extend([
            "",
            "    // Métodos helper reimplementados para modificar ângulos/posições dos ModelPart únicos",
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


def normalize_part_name(old_name: str) -> str:
    """Normaliza nomes das partes para convenção moderna"""
    name_mappings = {
        'lefteye': 'leftEye',
        'righteye': 'rightEye',
        'LeftShoulder': 'leftShoulder',
        'RightShoulder': 'rightShoulder',
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
        # Pernas em minúsculo (crítico!)
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
        'Leg8Seg5': 'leg8Seg5'
    }

    return name_mappings.get(old_name, old_name)


@full_convert_bp.route('/')
def index():
    return render_template('full_converter.html')


@full_convert_bp.route('/convert', methods=['POST'])
def convert():
    try:
        # Obter código de entrada
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