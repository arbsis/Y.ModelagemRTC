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
    """Converte dados de um array para um arquivo Excel usando XlsxWriter com suporte a múltiplos Dropdowns."""

    MIN_COLUMN_WIDTH = 10  # Largura mínima padrão para as colunas
    TABLE_START_ROW = 2    # Linha onde a tabela começa (após os títulos)

    workbook = xlsxwriter.Workbook(settings.file_name)
    worksheet = workbook.add_worksheet("Relatorio") # Nomeando a aba principal

    # --- LÓGICA DO MENU SUSPENSO (DATA VALIDATION) ---
    # Para cada coluna que precisa de validação, cria uma aba oculta específica
    dropdown_formulas = {} # Dicionário para mapear 'nome_coluna' -> 'formula_excel'

    for config in column_configs.values():
        if config.dropdown_values and len(config.dropdown_values) > 0:
            
            # Cria um nome seguro para a aba (Excel limita a 31 chars)
            # Adiciona o prefixo "_" para indicar que é auxiliar
            sheet_name = f"_{config.nome}"[:31]
            
            # Verifica se a aba já existe (para evitar erro se houver colunas com mesmo nome, o que seria estranho, mas seguro prevenir)
            if not workbook.get_worksheet_by_name(sheet_name):
                config_sheet = workbook.add_worksheet(sheet_name)
                config_sheet.hide() # Oculta a aba para o usuário final

                # Escreve os valores na coluna A da aba oculta específica
                for row_idx, val in enumerate(config.dropdown_values):
                    config_sheet.write(row_idx, 0, str(val))
                
                # Cria a referência apontando para a aba criada (Ex: ='_tipo_anexo'!$A$1:$A$50)
                last_row = len(config.dropdown_values)
                # O uso de aspas simples '{sheet_name}' na fórmula é vital caso o nome tenha espaços ou chars especiais
                formula = f"='{sheet_name}'!$A$1:$A${last_row}"
                
                # Guarda a fórmula associada ao nome da coluna
                dropdown_formulas[config.nome] = formula
    # ------------------------------------------------

    # Define formatos
    title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
    subtitle_format = workbook.add_format({'italic': True, 'align': 'center'})
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})  # Light gray background
    datetime_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm:ss'})

    # Criar um formato para exibir números como texto (evita a conversão para float)
    formato_numero = workbook.add_format({'num_format': '0'})  # O '0' força a exibição como inteiro

    # Escreve os títulos
    if settings.title_1:
        worksheet.merge_range(0, 0, 0, 9, settings.title_1, title_format)  # Adjust merge range to J1
    if settings.title_2:
        worksheet.merge_range(1, 0, 1, 9, settings.title_2, subtitle_format)  # Adjust merge range to J2

    # Prepara o cabeçalho
    header_row = []
    column_settings = []
    header_names = set()  # Usado para verificar nomes duplicados
    
    # Itera sobre as configurações para montar a ordem correta
    for i, column_config in enumerate(column_configs.values()):
        header_row.append((column_config.posicao, column_config.nome, column_config.titulo, column_config.somar, column_config.formato, column_config.data_type))
        
        header_name = column_config.titulo
        if header_name in header_names:
            header_name = f"{header_name} ({column_config.nome})"
        header_names.add(header_name)
        column_settings.append({'header': header_name})  # Add header titles to table format

    header_row.sort(key=lambda x: x[0])

    # Escreve o cabeçalho da tabela principal
    for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
        worksheet.write(TABLE_START_ROW, i, title, header_format)

    # Calcula largura máxima das colunas
    max_column_widths = {}
    for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
        column_letter = i  # Índice numérico da coluna
        max_width = max(MIN_COLUMN_WIDTH, len(title))  # Garante largura mínima

        # Itera sobre os dados para encontrar a largura máxima
        for row_index, row in enumerate(data):
            value = row[i]  # Acessa o valor pelo índice

            if value is None or value == "":
                continue  # Ignora valores nulos/vazios no cálculo da largura

            try:
                if data_type == 'datetime':
                    if isinstance(value, str):
                        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    value_str = value.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    value_str = str(value)  # Converte para string

                max_width = max(max_width, len(value_str))  # Atualiza a largura máxima
            except Exception as e:
                raise Exception(f"Erro ao processar a coluna '{title}': {e}")

        max_column_widths[column_letter] = max_width

    # Escreve os dados na tabela principal
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
                        if formato:  # A formatação é opcional por isso precisa verificar se existe
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
    if num_rows > 0:
        for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
            # Verifica se esta coluna possui uma fórmula de validação mapeada
            if nome in dropdown_formulas:
                formula_source = dropdown_formulas[nome]
                
                # Aplica validação da primeira linha de dados até a última
                worksheet.data_validation(
                    data_start_row, i,              # De: Linha X, Coluna Y
                    data_start_row + num_rows - 1, i, # Até: Linha Z, Coluna Y
                    {
                        'validate': 'list',
                        'source': formula_source,
                        'input_title': 'Selecione uma opção',
                        'input_message': 'Selecione um valor da lista',
                        'error_title': 'Entrada inválida',
                        'error_message': 'O valor inserido não pertence à lista permitida.'
                    }
                )
    # ---------------------------------------------------

    # Define a largura das colunas
    for column_letter, column_width in max_column_widths.items():
        worksheet.set_column(column_letter, column_letter, column_width + 2)  # Set column size

    # Implementar a Lógica de Soma (Totais)
    for i, (pos, nome, title, somar, formato, data_type) in enumerate(header_row):
        config = column_configs[nome]
        if config.somar:
            column_letter = i  # Coluna que está sendo somada
            start_row = TABLE_START_ROW + 1  # Começa na linha após o cabeçalho
            end_row = len(data) + TABLE_START_ROW  # A linha de dados termina antes da linha total

            # Use xlsxwriter.utility.xl_col_to_name to convert the row number to letter
            start_cell = xlsxwriter.utility.xl_col_to_name(column_letter) + str(start_row + 1)
            end_cell = xlsxwriter.utility.xl_col_to_name(column_letter) + str(end_row + 1)

            formula = f"=SUM({start_cell}:{end_cell})"  # Fórmula para soma
            format_sum = workbook.add_format({'bold': True})

            if formato:
                format_sum.set_num_format(formato)

            worksheet.write(data_start_row + len(data), i, formula, format_sum)  # Mostra resultado com a formatação

    # Cria a Tabela Visual (Estilo)
    num_cols = len(column_configs)
    table_options = {'columns': column_settings}
    if settings.table_style != "":
        table_options['style'] = settings.table_style
        
    worksheet.add_table(TABLE_START_ROW, 0, data_start_row + num_rows - 1, num_cols - 1, table_options)

    try:  # Tenta salvar o arquivo
        workbook.close()
        print(f"Arquivo Excel '{settings.file_name}' criado com sucesso.")
    except Exception as e:
        raise Exception(f"Erro ao salvar o arquivo Excel: {e}")

    return settings.file_name

if __name__ == '__main__':
    # 1. Simulação dos dados brutos do arquivo TXT (Lista Grande)
    lista_anexos = [
        "ART_9", "ART_147", "ANEXO_1", "ANEXO_2", "ANEXO_3", 
        "ANEXO_4_ART_131", "ANEXO_4_ART_144", "ANEXO_5_ART_132", 
        "ANEXO_5_ART_145", "ANEXO_6_ART_133", "ANEXO_6_ART_146", 
        "ANEXO_7", "ANEXO_8", "ANEXO_9", "ANEXO_10", 
        "ANEXO_11_ART_142_200043", "ANEXO_11_ART_142_200044", 
        "ANEXO_12", "ANEXO_13", "ANEXO_14", "ANEXO_15"
    ]

    # 2. Simulação de uma segunda lista para outra coluna (Lista Pequena)
    lista_status = ["PENDENTE", "APROVADO", "REJEITADO", "EM ANALISE"]

    # Dummy Data: Note que temos dados nas colunas que terão dropdown
    data = [
        [1, "João Silva", "ANEXO_1", "APROVADO", 150.00],
        [2, "Maria Souza", "ANEXO_15", "PENDENTE", 200.50],
        [3, "Pedro Santos", "ART_9", "REJEITADO", 50.00],
        [4, "Ana Costa", "", "", 120.00] # Exemplo vazio para testar dropdown
    ]

    settings = SettingPythonExcel(
        file_name='RelatorioMultiploDropdown.xlsx',
        title_1='Relatório Financeiro',
        title_2='Validação Múltipla de Dados',
        table_style="Table Style Medium 9"
    )

    column_configs = {
        "id": ColumnConfiguration(nome="id", titulo="ID", posicao=0, data_type="integer"),
        "cliente": ColumnConfiguration(nome="cliente", titulo="Nome do Cliente", posicao=1, data_type="string"),
        
        # COLUNA COM DROPDOWN 1 (ANEXOS)
        # Gera aba oculta: _tipo_anexo
        "tipo_anexo": ColumnConfiguration(
            nome="tipo_anexo", 
            titulo="Tipo de Anexo", 
            posicao=2, 
            data_type="string", 
            dropdown_values=lista_anexos
        ),

        # COLUNA COM DROPDOWN 2 (STATUS)
        # Gera aba oculta: _status_pagamento
        "status_pagamento": ColumnConfiguration(
            nome="status_pagamento",
            titulo="Status Atual",
            posicao=3,
            data_type="string",
            dropdown_values=lista_status
        ),

        "valor": ColumnConfiguration(nome="valor", titulo="Valor R$", posicao=4, formato="#,##0.00", somar=True, data_type="decimal"),
    }

    create_excel_from_data(data, settings, column_configs)