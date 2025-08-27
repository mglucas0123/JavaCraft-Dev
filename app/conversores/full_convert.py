import re
import javalang
from flask import Blueprint, jsonify, render_template, request

full_convert_bp = Blueprint('full_convert', __name__, template_folder='../templates')


class ModelPartData:
    def __init__(self, name):
        self.name = name
        self.texture_offset = (0, 0)
        self.add_box = None
        self.rotation_point = (0.0, 0.0, 0.0)
        self.initial_rotation = (0.0, 0.0, 0.0)
        self.mirror = False
        
    def __repr__(self):
        return f"Part(name={self.name}, offset={self.texture_offset}, box={self.add_box}, pivot={self.rotation_point}, rot={self.initial_rotation}, mirror={self.mirror})"


class ModelExtractor:
    def __init__(self, java_code):
        self.code = java_code
        self.tree = None
        self.class_name = "ConvertedModel"
        self.texture_width = 64
        self.texture_height = 64
        self.parts = {}
        self.animation_logic = []

    def _get_numeric_value(self, node):
        """Interpreta um nó da AST e retorna seu valor numérico, lidando com negativos."""
        if isinstance(node, javalang.tree.Literal):
            value_str = str(node.value).replace('F', '').replace('f', '').replace('D','').replace('d','')
            return float(value_str)
        if isinstance(node, javalang.tree.UnaryOperation) and node.operator == '-':
            return -1 * self._get_numeric_value(node.operand)
        return 0.0

    def parse(self):
        try:
            self.tree = javalang.parse.parse(self.code)
            if self.tree.types and isinstance(self.tree.types[0], javalang.tree.ClassDeclaration):
                self.class_name = self.tree.types[0].name
            else:
                class_declarations = list(self.tree.filter(javalang.tree.ClassDeclaration))
                if not class_declarations: 
                    raise ValueError("Nenhuma classe Java encontrada.")
                self.class_name = class_declarations[0][1].name
            return True, None
        except Exception as e:
            return False, f"Erro na análise do código: {e}"

    def extract_data(self):
        if not self.tree: 
            return False, "Código não analisado."
        
        constructors = list(self.tree.filter(javalang.tree.ConstructorDeclaration))
        if constructors:
            self._extract_from_constructor(constructors[0][1].body)
        
        render_methods = [m for m in self.tree.filter(javalang.tree.MethodDeclaration) if m[1].name == 'render']
        if render_methods:
            self._extract_from_render(render_methods[0][1].body)
            
        return True, "Extração concluída."

    def _extract_from_constructor(self, body):
        """Extrai dados das partes do modelo a partir do construtor."""
        lines = self.code.splitlines()
        
        for stmt in body:
            if not hasattr(stmt, 'position') or stmt.position is None: 
                continue
                
            if stmt.position.line <= len(lines):
                line = lines[stmt.position.line - 1].strip()
                
                texture_match = re.search(r"(textureWidth|textureHeight)\s*=\s*(\d+)", line)
                if texture_match:
                    key, value = texture_match.groups()
                    if key == "textureWidth": 
                        self.texture_width = int(value)
                    elif key == "textureHeight": 
                        self.texture_height = int(value)
                    continue
                
                init_match = re.search(r"\((?:this\.)?(\w+)\s*=\s*new\s+ModelRenderer\(\s*(?:\([^)]*\))?\s*this\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", line)
                if init_match:
                    part_name, u, v = init_match.groups()
                    if part_name not in self.parts:
                        self.parts[part_name] = ModelPartData(part_name)
                    self.parts[part_name].texture_offset = (int(u), int(v))
                    continue
                
                self._extract_part_properties(line)
                
    def _extract_part_properties(self, line):
        """Extrai propriedades específicas de cada parte."""
        part_match = re.match(r"(?:this\.)?(\w+)\.", line)
        if not part_match:
            return
            
        part_name = part_match.group(1)
        if part_name not in self.parts:
            self.parts[part_name] = ModelPartData(part_name)
        
        part = self.parts[part_name]
        
        box_match = re.search(r"\.addBox\s*\(\s*([^)]+)\)", line)
        if box_match:
            args_str = box_match.group(1)
            try:
                args = [float(arg.strip().replace('f', '').replace('F', '')) for arg in args_str.split(',')]
                if len(args) >= 6:
                    part.add_box = tuple(args[:6])  # x, y, z, width, height, depth
            except (ValueError, IndexError):
                pass
                
        rot_match = re.search(r"\.setRotationPoint\s*\(\s*([^)]+)\)", line)
        if rot_match:
            args_str = rot_match.group(1)
            try:
                args = [float(arg.strip().replace('f', '').replace('F', '')) for arg in args_str.split(',')]
                if len(args) >= 3:
                    part.rotation_point = tuple(args[:3])
            except (ValueError, IndexError):
                pass
                
        mirror_match = re.search(r"\.mirror\s*=\s*(true|false)", line)
        if mirror_match:
            part.mirror = (mirror_match.group(1) == 'true')
            
        setrot_match = re.search(r"setRotation\s*\(\s*" + re.escape(part_name) + r"\s*,\s*([^)]+)\)", line)
        if setrot_match:
            args_str = setrot_match.group(1)
            try:
                args = [float(arg.strip().replace('f', '').replace('F', '')) for arg in args_str.split(',')]
                if len(args) >= 3:
                    part.initial_rotation = tuple(args[:3])
            except (ValueError, IndexError):
                pass

    def _extract_from_render(self, body):
        """Extrai lógica de animação do método render."""
        lines = self.code.splitlines()
        for stmt in body:
            if hasattr(stmt, 'position') and stmt.position and stmt.position.line <= len(lines):
                line_content = lines[stmt.position.line - 1].strip()
                # Filtrar apenas linhas relevantes de animação
                if (line_content and 
                    "super.render" not in line_content and 
                    "setRotationAngles" not in line_content and
                    ".render(" not in line_content and
                    not line_content.startswith("//") and
                    line_content != "{" and line_content != "}"):
                    self.animation_logic.append(line_content)


class CodeGenerator:
    def __init__(self, data):
        self.data = data
        self.class_name = data['class_name']
        self.parts = data['parts']

    def generate(self):
        """Gera o código completo do modelo 1.21.1."""
        imports = self._generate_imports()
        class_decl = f"public class {self.class_name}<T extends Entity> extends EntityModel<T>"
        fields = self._generate_fields()
        constructor = self._generate_constructor()
        layer_def = self._generate_create_body_layer()
        setup_anim = self._generate_setup_anim()
        render_buffer = self._generate_render_to_buffer()
        root_method = self._generate_root_method()
        
        return f"""{imports}

{class_decl} {{
{fields}

{constructor}

{layer_def}

{setup_anim}

{render_buffer}

{root_method}
}}"""

    def _generate_imports(self):
        return """import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.*;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;"""

    def _generate_fields(self):
        """Gera campos do modelo seguindo a hierarquia 1.21.1."""
        field_lines = ["    private final ModelPart root;"]
        part_names = sorted(self.parts.keys())
        field_lines.extend([f"    private final ModelPart {name};" for name in part_names])
        return "\n".join(field_lines)

    def _generate_constructor(self):
        """Gera construtor seguindo padrão 1.21.1."""
        part_names = sorted(self.parts.keys())
        constructor_lines = ["        this.root = root;"]
        constructor_lines.extend([f"        this.{name} = root.getChild(\"{name}\");" for name in part_names])
        body = "\n".join(constructor_lines)
        
        return f"""    public {self.class_name}(ModelPart root) {{
{body}
    }}"""

    def _generate_create_body_layer(self):
        """Gera o método createBodyLayer com todas as partes definidas corretamente."""
        width, height = self.data['texture_size']
        part_def_lines = []
        part_names = sorted(self.parts.keys())

        for name in part_names:
            part_data = self.parts[name]
            u, v = part_data['texture_offset']
            
            # Construir CubeListBuilder
            cubebuilder = f"CubeListBuilder.create().texOffs({u}, {v})"
            
            if part_data['mirror']:
                cubebuilder += ".mirror()"
            
            # Adicionar geometria se disponível
            if part_data['add_box'] and len(part_data['add_box']) >= 6:
                x, y, z, w, h, d = part_data['add_box']
                cubebuilder += f".addBox({x}F, {y}F, {z}F, {w}F, {h}F, {d}F)"
            
            # Definir posição e rotação
            px, py, pz = part_data['rotation_point']
            rx, ry, rz = part_data['initial_rotation']
            
            partpose = f"PartPose.offsetAndRotation({px}F, {py}F, {pz}F, {rx}F, {ry}F, {rz}F)"
            
            part_def_lines.append(f'        partdefinition.addOrReplaceChild("{name}", {cubebuilder}, {partpose});')

        body = "\n".join(part_def_lines)
        
        return f"""    public static LayerDefinition createBodyLayer() {{
        MeshDefinition meshdefinition = new MeshDefinition();
        PartDefinition partdefinition = meshdefinition.getRoot();

{body}

        return LayerDefinition.create(meshdefinition, {width}, {height});
    }}"""

    def _generate_setup_anim(self):
        """Gera setupAnim vazio conforme solicitado."""
        return """    @Override
    public void setupAnim(T entity, float limbSwing, float limbSwingAmount, float ageInTicks, float netHeadYaw, float headPitch) {
        // Animação removida conforme solicitado - modelo apenas estrutural
    }"""
    
    def _generate_render_to_buffer(self):
        """Gera renderToBuffer seguindo padrão 1.21.1."""
        return """    @Override
    public void renderToBuffer(PoseStack poseStack, VertexConsumer vertexConsumer, int packedLight, int packedOverlay, int color) {
        root.render(poseStack, vertexConsumer, packedLight, packedOverlay, color);
    }"""
    
    def _generate_root_method(self):
        """Gera o método root() necessário para EntityModel."""
        return """    @Override
    public ModelPart root() {
        return this.root;
    }"""

@full_convert_bp.route('/')
def index():
    """Renderiza a página inicial do conversor."""
    return render_template('full_converter.html', original_code='', converted_code=None, error=None)

@full_convert_bp.route('/convert', methods=['POST'])
def convert_code():
    """Recebe o código via AJAX, executa a conversão e retorna o resultado em JSON."""
    try:
        old_code = request.form.get('code_input', '')
        if not old_code:
            return jsonify({'error': 'Nenhum código foi fornecido.'}), 400

        extractor = ModelExtractor(old_code)
        
        parse_success, message = extractor.parse()
        if not parse_success:
            return jsonify({'error': message}), 400
            
        extract_success, message = extractor.extract_data()
        if not extract_success:
            return jsonify({'error': message}), 400

        if not extractor.parts:
            return jsonify({'error': 'Nenhuma parte do modelo foi encontrada. Verifique se o código contém definições de ModelRenderer.'}), 400

        extracted_data_dict = {
            "class_name": extractor.class_name,
            "texture_size": (extractor.texture_width, extractor.texture_height),
            "parts": {name: part.__dict__ for name, part in extractor.parts.items()},
            "animation_logic": extractor.animation_logic
        }

        code_generator = CodeGenerator(extracted_data_dict)
        new_code = code_generator.generate()
        
        return jsonify({'converted_code': new_code})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro interno no servidor: {str(e)}'}), 500
