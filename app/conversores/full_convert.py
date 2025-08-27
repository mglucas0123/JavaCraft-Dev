import re
from typing import Dict, List, Tuple, Optional
from flask import Blueprint, render_template, request, jsonify

full_convert_bp = Blueprint('full_convert', __name__)

@full_convert_bp.route('/')
def index():
    return render_template('full_converter.html')

@full_convert_bp.route('/convert', methods=['POST'])
def convert():
    try:
        # Obter código de entrada
        code_input = request.form.get('code_input', '').strip()
        
        if not code_input:
            return jsonify({'error': 'Código de entrada não pode estar vazio'}), 400
        
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


class ModelConverter:

    def __init__(self):
        self.texture_width = 256
        self.texture_height = 128
        self.parts_data = {}
        self.animation_methods = []
        self.entity_name = ""

    def convert_model(self, java_code: str) -> str:
        """Converte um modelo 1.7.10 para 1.21.1"""
        try:
            # Extrair informações básicas
            self._extract_basic_info(java_code)

            # Mapear todas as partes do modelo
            self._extract_model_parts(java_code)

            # Extrair métodos de animação
            self._extract_animation_methods(java_code)

            # Gerar código 1.21.1
            return self._generate_modern_model()

        except Exception as e:
            raise Exception(f"Erro na conversão: {str(e)}")

    def _extract_basic_info(self, java_code: str):
        """Extrai informações básicas do modelo"""
        # Nome da classe
        class_match = re.search(r'public class (\w+) extends ModelBase',
                                java_code)
        if class_match:
            self.entity_name = class_match.group(1).replace('Model', '')

        # Dimensões da textura
        texture_width_match = re.search(r'this\.textureWidth = (\d+)',
                                        java_code)
        texture_height_match = re.search(r'this\.textureHeight = (\d+)',
                                         java_code)

        if texture_width_match:
            self.texture_width = int(texture_width_match.group(1))
        if texture_height_match:
            self.texture_height = int(texture_height_match.group(1))

    def _extract_model_parts(self, java_code: str):
        """Extrai todas as partes do modelo e suas configurações"""
        # Encontrar todas as declarações de ModelRenderer
        part_declarations = re.findall(r'ModelRenderer (\w+);', java_code)

        for part_name in part_declarations:
            # Encontrar a configuração desta parte
            part_config = self._extract_part_config(java_code, part_name)
            if part_config:
                self.parts_data[part_name] = part_config

    def _extract_part_config(self, java_code: str,
                             part_name: str) -> Optional[Dict]:
        """Extrai a configuração de uma parte específica"""
        # Padrão para encontrar a configuração completa da parte
        pattern = rf'\(this\.{part_name} = new ModelRenderer.*?\)\)\.addBox\((.*?)\);.*?{part_name}\.setRotationPoint\((.*?)\);.*?this\.setRotation\(this\.{part_name}, (.*?)\);'

        match = re.search(pattern, java_code, re.DOTALL)
        if not match:
            return None

        # Extrair informações da addBox
        addbox_params = [p.strip() for p in match.group(1).split(',')]
        if len(addbox_params) >= 6:
            x_offset = float(addbox_params[0].replace('f', ''))
            y_offset = float(addbox_params[1].replace('f', ''))
            z_offset = float(addbox_params[2].replace('f', ''))
            width = int(addbox_params[3])
            height = int(addbox_params[4])
            depth = int(addbox_params[5])
        else:
            return None

        # Extrair posição
        position_params = [p.strip() for p in match.group(2).split(',')]
        if len(position_params) >= 3:
            pos_x = float(position_params[0].replace('f', ''))
            pos_y = float(position_params[1].replace('f', ''))
            pos_z = float(position_params[2].replace('f', ''))
        else:
            pos_x = pos_y = pos_z = 0.0

        # Extrair rotação
        rotation_params = [p.strip() for p in match.group(3).split(',')]
        if len(rotation_params) >= 3:
            rot_x = float(rotation_params[0].replace('f', ''))
            rot_y = float(rotation_params[1].replace('f', ''))
            rot_z = float(rotation_params[2].replace('f', ''))
        else:
            rot_x = rot_y = rot_z = 0.0

        # Extrair coordenadas da textura
        texture_match = re.search(rf'new ModelRenderer.*?this, (\d+), (\d+)\)',
                                  java_code)
        tex_u = tex_v = 0
        if texture_match:
            tex_u = int(texture_match.group(1))
            tex_v = int(texture_match.group(2))

        return {
            'addBox': {
                'x': x_offset,
                'y': y_offset,
                'z': z_offset,
                'width': width,
                'height': height,
                'depth': depth
            },
            'position': {
                'x': pos_x,
                'y': pos_y,
                'z': pos_z
            },
            'rotation': {
                'x': rot_x,
                'y': rot_y,
                'z': rot_z
            },
            'texture': {
                'u': tex_u,
                'v': tex_v
            }
        }

    def _extract_animation_methods(self, java_code: str):
        """Extrai métodos de animação personalizados"""
        # Encontrar métodos como doLeftLeg, doRightLeg, doTail, etc.
        method_pattern = r'private void (do\w+)\((.*?)\) \{(.*?)\}'
        methods = re.findall(method_pattern, java_code, re.DOTALL)

        for method_name, params, body in methods:
            self.animation_methods.append({
                'name': method_name,
                'params': params,
                'body': body.strip()
            })

    def _generate_modern_model(self) -> str:
        """Gera o código do modelo modernizado para 1.21.1"""
        class_name = f"{self.entity_name}Model"

        # Cabeçalho
        code = f'''package mglucas0123.entities.models;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.model.HierarchicalModel;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.*;
import net.minecraft.util.Mth;
import net.minecraft.resources.ResourceLocation;
import mglucas0123.entities.{self.entity_name}Entity;

public class {class_name} extends HierarchicalModel<{self.entity_name}Entity> {{
    private final ModelPart root;
'''

        # Declarar todas as partes
        for part_name in self.parts_data.keys():
            code += f"    private final ModelPart {part_name};\n"

        # Construtor
        code += f'''
    public {class_name}(ModelPart root) {{
        this.root = root;
'''

        for part_name in self.parts_data.keys():
            code += f'        this.{part_name} = root.getChild("{part_name}");\n'

        code += "    }\n\n"

        # Método createBodyLayer
        code += f'''    public static LayerDefinition createBodyLayer() {{
        MeshDefinition meshdefinition = new MeshDefinition();
        PartDefinition partdefinition = meshdefinition.getRoot();

'''

        # Definir todas as partes
        for part_name, config in self.parts_data.items():
            addbox = config['addBox']
            pos = config['position']
            rot = config['rotation']
            tex = config['texture']

            code += f'''        partdefinition.addOrReplaceChild("{part_name}",
            CubeListBuilder.create()
                .texOffs({tex['u']}, {tex['v']})
                .addBox({addbox['x']}f, {addbox['y']}f, {addbox['z']}f, 
                       {addbox['width']}, {addbox['height']}, {addbox['depth']}),
            PartPose.offsetAndRotation({pos['x']}f, {pos['y']}f, {pos['z']}f,
                                     {rot['x']}f, {rot['y']}f, {rot['z']}f));

'''

        code += f'''        return LayerDefinition.create(meshdefinition, {self.texture_width}, {self.texture_height});
    }}

'''

        # Método root
        code += '''    @Override
    public ModelPart root() {
        return this.root;
    }

'''

        # Método setupAnim (vazio conforme solicitado)
        code += f'''    @Override
    public void setupAnim({self.entity_name}Entity entity, float limbSwing, float limbSwingAmount, 
                         float ageInTicks, float netHeadYaw, float headPitch) {{
        // Animações serão implementadas posteriormente
        // TODO: Transferir lógica de animação dos métodos do modelo original
'''

        # Adicionar comentários sobre os métodos de animação encontrados
        if self.animation_methods:
            code += "\n        // Métodos de animação detectados no modelo original:\n"
            for method in self.animation_methods:
                code += f"        // - {method['name']}({method['params']})\n"

        code += "    }\n"

        # Adicionar métodos de animação como comentários para referência
        if self.animation_methods:
            code += "\n    /* MÉTODOS DE ANIMAÇÃO ORIGINAIS PARA REFERÊNCIA:\n"
            for method in self.animation_methods:
                code += f"\n    // Método: {method['name']}\n"
                code += f"    // Parâmetros: {method['params']}\n"
                code += f"    // Corpo original:\n"
                # Comentar cada linha do corpo
                for line in method['body'].split('\n'):
                    if line.strip():
                        code += f"    // {line}\n"
                code += "\n"
            code += "    */\n"

        code += "}"

        return code


def convert_model_code(input_code: str) -> str:
    """Função principal para converter código de modelo"""
    if not input_code or not input_code.strip():
        raise ValueError("Código de entrada não pode estar vazio")

    # Verificar se é um modelo 1.7.10 válido
    if "extends ModelBase" not in input_code:
        raise ValueError(
            "O código fornecido não parece ser um modelo ModelBase válido")

    if "ModelRenderer" not in input_code:
        raise ValueError("O código não contém declarações ModelRenderer")

    converter = ModelConverter()
    return converter.convert_model(input_code)
