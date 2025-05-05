# Caminhos de arquivos CSV de dados brutos (utilizados em captacao_e_geracao_dados.carregar_dados_brutos)
DESPESAS_VIAGEM_FILE = "reinan_costa_despesas_de_viagem_db.csv"      # Despesas variáveis de viagem
DESPESAS_FIXAS_FILE = "reinan_costa_despesas_fixas_db.csv"           # Despesas fixas mensais
MOTORISTA_FILE = "reinan_costa_motorista_db.csv"                     # Dados dos motoristas
VEICULO_FILE = "reinan_costa_veiculo_db.csv"                         # Dados dos veículos
VIAGEM_COMPLETA_FILE = "reinan_costa_viagem_completa.csv"            # Dados completos das viagens

# Credenciais de login (utilizadas na função de autenticação em dashboard.py)
USUARIO = "carlos"
SENHA   = "110712"

# Limites numéricos para validações de consistência de dados (usados em utils_validacao.py)
CONSUMO_MINIMO_KM_L       = 1.0  # km/L mínimo esperado (consumo muito baixo gera alerta)
CONSUMO_MAXIMO_KM_L       = 3.5  # km/L máximo esperado (consumo muito alto gera alerta)
PRECO_DIESEL_MINIMO_R_L   = 3.0  # R$/L mínimo aceitável (preço do diesel muito baixo gera alerta)
PRECO_DIESEL_MAXIMO_R_L   = 8.0  # R$/L máximo aceitável (preço do diesel muito alto gera alerta)
MAX_LINHAS_PREVIEW_ANOMALIAS = 5  # número máximo de linhas detalhadas nos relatórios de anomalias

# Filtros estáticos aplicados aos dados brutos (e.g., exclusão de status indesejados)
STATUS_EXCLUIDOS = ["NAO INICIADA", "EM VIAGEM"]  # Viagens nesses status são ignoradas no enriquecimento de dados

# Categorias de despesas e manutenções (usadas para filtragem e cálculos de indicadores)
CATEGORIA_COMBUSTIVEL = "COMBUSTIVEL"   # Identificador para despesas de combustível (combustível)
CATEGORIA_CAPEX       = "PRESTACAO"     # Identificador para despesas de CAPEX (ex.: prestação de veículo)
CATEGORIA_PNEU        = "PNEU"          # Identificador para despesas relacionadas a pneus

# Listas de categorias de manutenção (manutenções e serviços), em diferentes contextos:
CATEGORIAS_MANUTENCAO_VIAGEM = ["manutencao", "borracharia", "lavagem"]  # categorias de despesas de viagem (minúsculas)
CATEGORIAS_MANUTENCAO_FIXAS  = ["manutencao", "borracharia", "plano manutencao", "pneu", "lavagem", "mecanico", "filtros", "pneu coberto"]  # categorias de despesas fixas (minúsculas)

CATEGORIAS_MANUTENCAO_VIAGEM_UPPER = ["MANUTENCAO", "BORRACHARIA", "LAVAGEM"]  # categorias de despesas de viagem (maiúsculas)
CATEGORIAS_MANUTENCAO_FIXAS_UPPER  = ["MANUTENCAO", "BORRACHARIA", "PLANO MANUTENCAO", "PNEU", "LAVAGEM", "MECANICO"]  # categorias de despesas fixas (maiúsculas)

CATEGORIAS_IMPOSTO = ["IMPOSTO", "DETRAN"]  # Categorias de despesas consideradas impostos (excluídas de certas somas)

# Parâmetros padrão para cálculo de comissão (utilizados em utils_comissao.py)
DEFAULT_CONFIG = {
    "INCREMENTO_CONSUMO_MAXIMO": 0.30,   # Incremento de consumo +30% (limite para score_consumo = 1)
    "INCREMENTO_RECEITA_MAXIMO": 1.30,   # Incremento de receita +130% (limite para score_receita = 1)

    "PESO_CONSUMO": 0.70,                # Peso do consumo no cálculo da nota de desempenho
    "PESO_RECEITA": 0.30,                # Peso da receita no cálculo da nota de desempenho

    "DIAS_OCIOSIDADE_NORMAL": 4,         # Dias ociosos sem penalização
    "DIAS_OCIOSIDADE_PLENO": 10,         # Dias ociosos para penalização máxima
    "PENALIDADE_OCIOSIDADE_MAX": 0.30,   # Penalização máxima de -30% na nota final por ociosidade

    "COMISSAO_MAXIMA": 500.00,           # Valor máximo de comissão possível
    "COMISSAO_MINIMA": 150.00,           # Valor mínimo de comissão (garantido se nota > 0)

    "JANELA_HISTORICO_DIAS": 90,         # Janela de histórico (dias) para comparação de desempenho
    "COLUNA_RECEITA": "lucro_bruto",     # Nome da coluna de receita utilizada no cálculo
}

NOTA_BASE           = 0.50  # Pontuação base (baseline) para nota de desempenho do motorista
PESO_NOTA_ADICIONAL = 0.50  # Peso da parcela variável da nota (somado à NOTA_BASE totaliza 1.0 na nota máxima)
