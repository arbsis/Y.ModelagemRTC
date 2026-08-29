import xlsxwriter
from datetime import datetime

class ColumnConfiguration:
    """Configurações das colunas do Excel."""
    def __init__(self, nome="", titulo="", somar=False, posicao=0, formato="", data_type=None, dropdown_values=None):
        self.nome = nome            # Nome da coluna (correspondente ao campo no dataset)
        self.titulo = titulo        # Título da coluna no Excel
        self.somar = somar          # Indica se a coluna deve ser somada
        self.posicao = posicao      # Posição da coluna
        self.formato = formato      # Formato da coluna (ex: '#0.00')
        self.data_type = data_type  # Tipo de dado ('string', 'datetime', 'integer', 'decimal' or None)
        self.dropdown_values = dropdown_values # Lista de valores para o menu suspenso (List[str] ou None)

class SettingPythonExcel:
    """Configurações gerais do Excel."""
    def __init__(self, file_name="", title_1="", title_2="", table_style=""):
        self.file_name = file_name    # Nome do arquivo Excel
        self.title_1 = title_1        # Título principal do relatório
        self.title_2 = title_2        # Subtítulo do relatório
        self.table_style = table_style # Estilo da tabela ("Table Style Medium 9")

def create_excel_from_data(data, settings, column_configs):
    """Converte dados de um array para um arquivo Excel usando XlsxWriter com suporte a Dropdown."""

    MIN_COLUMN_WIDTH = 10  # Largura mínima padrão para as colunas
    TABLE_START_ROW = 2    # Linha onde a tabela começa (após os títulos)

    workbook = xlsxwriter.Workbook(settings.file_name)
    worksheet = workbook.add_worksheet("Relatorio") # Nomeando a aba principal

    # --- LÓGICA DO MENU SUSPENSO (DATA VALIDATION) ---
    # Verifica se alguma coluna precisa de dropdown para criar a aba de configuração
    config_sheet = None
    config_col_idx = 0
    dropdown_formulas = {} # Dicionário para mapear 'nome_coluna' -> 'formula_excel'

    for config in column_configs.values():
        if config.dropdown_values and len(config.dropdown_values) > 0:
            if config_sheet is None:
                config_sheet = workbook.add_worksheet("_Config")
                config_sheet.hide() # Oculta a aba para o usuário final

            # Escreve os valores na aba de configuração
            for row_idx, val in enumerate(config.dropdown_values):
                config_sheet.write(row_idx, config_col_idx, str(val))
            
            # Cria a referência (Ex: =_Config!$A$1:$A$50)
            col_letter = xlsxwriter.utility.xl_col_to_name(config_col_idx)
            last_row = len(config.dropdown_values)
            formula = f"='_Config'!${col_letter}$1:${col_letter}${last_row}"
            
            # Guarda a fórmula associada ao nome da coluna de configuração
            dropdown_formulas[config.nome] = formula
            config_col_idx += 1
    # ------------------------------------------------

    # Define formatos
    title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
    subtitle_format = workbook.add_format({'italic': True, 'align': 'center'})
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
    datetime_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm:ss'})
    formato_numero = workbook.add_format({'num_format': '0'})

    # Escreve os títulos
    if settings.title_1:
        worksheet.merge_range(0, 0, 0, 9, settings.title_1, title_format)
    if settings.title_2:
        worksheet.merge_range(1, 0, 1, 9, settings.title_2, subtitle_format)

    # Prepara o cabeçalho
    header_row = []
    column_settings = []
    header_names = set()
    
    # Itera sobre as configurações para montar a ordem correta
    for i, column_config in enumerate(column_configs.values()):
        # Adicionei column_config.nome na tupla para recuperar a chave depois
        header_row.append((column_config.posicao, column_config.nome, column_config.titulo, column_config.somar, column_config.formato, column_config.data_type))
        
        header_name = column_config.titulo
        if header_name in header_names:
            header_name = f"{header_name} ({column_config.nome})"
        header_names.add(header_name)
        column_settings.append({'header': header_name})

    header_row.sort(key=lambda x: x[0])

    # Escreve o cabeçalho
    for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
        worksheet.write(TABLE_START_ROW, i, title, header_format)

    # Calcula largura máxima (Lógica mantida original)
    max_column_widths = {}
    for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
        column_letter = i
        max_width = max(MIN_COLUMN_WIDTH, len(title))
        for row_index, row in enumerate(data):
            value = row[i]
            if value is None or value == "":
                continue
            try:
                if data_type == 'datetime':
                    if isinstance(value, str):
                        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    value_str = value.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    value_str = str(value)
                max_width = max(max_width, len(value_str))
            except Exception as e:
                # Log opcional aqui
                pass
        max_column_widths[column_letter] = max_width

    # Escreve os dados
    data_start_row = TABLE_START_ROW + 1
    num_rows = len(data)
    
    for row_index, row in enumerate(data):
        for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
            value = row[i]
            try:
                current_row = data_start_row + row_index
                if value is not None and value != "":
                    if data_type == 'datetime':
                        if isinstance(value, str):
                            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        worksheet.write_datetime(current_row, i, value, datetime_format)
                    elif data_type == 'integer':
                        worksheet.write_number(current_row, i, value, formato_numero)
                    else:
                        if formato:
                            num_format = workbook.add_format({'num_format': formato})
                            if isinstance(value, str):
                                worksheet.write_string(current_row, i, value)
                            else:
                                worksheet.write_number(current_row, i, value, num_format)
                        else:
                            worksheet.write_string(current_row, i, str(value))
                elif value is None:
                    worksheet.write(current_row, i, "")
                else:
                    worksheet.write(current_row, i, str(value))
            except Exception as e:
                 raise Exception(f"Erro ao formatar a coluna '{title}': {e}")

    # --- APLICA A VALIDAÇÃO DE DADOS (MENU SUSPENSO) ---
    # Aplicamos após escrever os dados. A validação fica "por cima" das células.
    if num_rows > 0:
        for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
            # Se esta coluna tem uma fórmula de validação preparada
            if nome in dropdown_formulas:
                formula_source = dropdown_formulas[nome]
                
                # Aplica validação da primeira linha de dados até a última
                worksheet.data_validation(
                    data_start_row, i,              # Primeira célula (Linha, Coluna)
                    data_start_row + num_rows - 1, i, # Última célula (Linha, Coluna)
                    {
                        'validate': 'list',
                        'source': formula_source,
                        'input_title': 'Selecione uma opção',
                        'input_message': 'Escolha um valor da lista',
                        'error_title': 'Entrada inválida',
                        'error_message': 'Por favor, selecione um valor válido da lista suspensa.'
                    }
                )
    # ---------------------------------------------------

    # Define a largura das colunas
    for column_letter, column_width in max_column_widths.items():
        worksheet.set_column(column_letter, column_letter, column_width + 2)

    # Implementar a Lógica de Soma
    for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
        config = column_configs[nome]
        if config.somar:
            column_letter = i
            start_row = TABLE_START_ROW + 1
            end_row = len(data) + TABLE_START_ROW
            
            start_cell = xlsxwriter.utility.xl_col_to_name(column_letter) + str(start_row + 1)
            end_cell = xlsxwriter.utility.xl_col_to_name(column_letter) + str(end_row + 1)

            formula = f"=SUM({start_cell}:{end_cell})"
            format_sum = workbook.add_format({'bold': True})

            if formato:
                format_sum.set_num_format(formato)

            worksheet.write(data_start_row + len(data), i, formula, format_sum)

    # Add the table
    num_cols = len(column_configs)
    table_options = {'columns': column_settings}
    if settings.table_style != "":
        table_options['style'] = settings.table_style
        
    worksheet.add_table(TABLE_START_ROW, 0, data_start_row + num_rows - 1, num_cols - 1, table_options)

    try:
        workbook.close()
        print(f"Arquivo Excel '{settings.file_name}' criado com sucesso.")
    except Exception as e:
        raise Exception(f"Erro ao salvar o arquivo Excel: {e}")

    return settings.file_name

if __name__ == '__main__':
    # Simulação dos dados brutos (O seu vem do MenuSuspenso.txt)
    lista_anexos = [
        "ART_9", "ART_147", "ANEXO_1", "ANEXO_2", "ANEXO_3", 
        "ANEXO_4_ART_131", "ANEXO_4_ART_144", "ANEXO_5_ART_132", 
        "ANEXO_5_ART_145", "ANEXO_6_ART_133", "ANEXO_6_ART_146", 
        "ANEXO_7", "ANEXO_8", "ANEXO_9", "ANEXO_10", 
        "ANEXO_11_ART_142_200043", "ANEXO_11_ART_142_200044", 
        "ANEXO_12", "ANEXO_13", "ANEXO_14", "ANEXO_15"
    ]

    # Dummy Data (Exemplo de dados vindo do Delphi)
    # Note que a coluna 'tipo_anexo' já vem com dados preenchidos ("ANEXO_1", etc.)
    data = [
        [1, "João Silva", "ANEXO_1", 150.00],
        [2, "Maria Souza", "ANEXO_15", 200.50],
        [3, "Pedro Santos", "ART_9", 50.00]
    ]

    settings = SettingPythonExcel(
        file_name='RelatorioComValidacao.xlsx',
        title_1='Relatório Financeiro',
        title_2='Validação de Anexos',
        table_style="Table Style Medium 9"
    )

    column_configs = {
        "id": ColumnConfiguration(nome="id", titulo="ID", posicao=0, data_type="integer"),
        "cliente": ColumnConfiguration(nome="cliente", titulo="Nome do Cliente", posicao=1, data_type="string"),
        # AQUI ESTÁ A MÁGICA: Passamos a lista para o dropdown_values
        "tipo_anexo": ColumnConfiguration(
            nome="tipo_anexo", 
            titulo="Tipo de Anexo", 
            posicao=2, 
            data_type="string", 
            dropdown_values=lista_anexos
        ),
        "valor": ColumnConfiguration(nome="valor", titulo="Valor R$", posicao=3, formato="#,##0.00", somar=True, data_type="decimal"),
    }

    create_excel_from_data(data, settings, column_configs)