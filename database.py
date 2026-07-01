import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get('TECOS_DB_PATH', str(Path(__file__).resolve().parent / 'tecos.db')))
if DB_PATH.parent != Path('.') and not DB_PATH.parent.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            endereco TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            descricao_problema TEXT NOT NULL,
            tipo_servico TEXT NOT NULL,
            valor_material REAL NOT NULL,
            valor_mao_de_obra REAL NOT NULL,
            valor_total REAL NOT NULL,
            status TEXT NOT NULL,
            data_abertura TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ordem_servico_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordem_id INTEGER NOT NULL,
            servico TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            valor_unitario REAL NOT NULL,
            valor_total REAL NOT NULL,
            FOREIGN KEY (ordem_id) REFERENCES ordens_servico(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


def get_servicos():
    return [
        {'nome': 'Quebrar', 'valor': 15.00, 'unidade': 'a Unidade'},
        {'nome': 'Tomada', 'valor': 35.00, 'unidade': 'a Unidade'},
        {'nome': 'Interruptor Lampada', 'valor': 25.00, 'unidade': 'a Unidade'},
        {'nome': 'Puxar Fios', 'valor': 15.00, 'unidade': 'o Metro'},
        {'nome': 'Quadro de Distribuição', 'valor': 300.00, 'unidade': 'a Unidade'},
        {'nome': 'Padrão da Concecionaria', 'valor': 250.00, 'unidade': 'a Unidade'},
    ]


def listar_clientes():
    conn = get_connection()
    clientes = conn.execute('SELECT * FROM clientes ORDER BY nome').fetchall()
    conn.close()
    return clientes


def adicionar_cliente(nome, telefone, endereco):
    conn = get_connection()
    conn.execute(
        'INSERT INTO clientes (nome, telefone, endereco) VALUES (?, ?, ?)',
        (nome, telefone, endereco),
    )
    conn.commit()
    conn.close()


def listar_ordens(status=None, limit=None, cliente_id=None, data_inicio=None, data_fim=None):
    conn = get_connection()
    query = '''
        SELECT os.id, os.cliente_id, os.descricao_problema, os.tipo_servico,
               os.valor_material, os.valor_mao_de_obra, os.valor_total,
               os.status, os.data_abertura, c.nome AS cliente_nome
        FROM ordens_servico AS os
        INNER JOIN clientes AS c ON c.id = os.cliente_id
        WHERE 1 = 1
    '''
    params = []
    if status:
        query += ' AND os.status = ?'
        params.append(status)
    if cliente_id:
        query += ' AND os.cliente_id = ?'
        params.append(cliente_id)
    if data_inicio:
        query += ' AND os.data_abertura >= ?'
        params.append(data_inicio)
    if data_fim:
        query += ' AND os.data_abertura <= ?'
        params.append(data_fim)
    query += ' ORDER BY os.id DESC'
    if limit:
        query += f' LIMIT {limit}'
    ordens = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    return ordens


def adicionar_ordem(cliente_id, descricao_problema, tipo_servico, valor_material, valor_mao_de_obra, status, data_abertura, servicos=None):
    valor_total = float(valor_material) + float(valor_mao_de_obra)
    conn = get_connection()
    cursor = conn.execute(
        '''
        INSERT INTO ordens_servico (
            cliente_id, descricao_problema, tipo_servico, valor_material,
            valor_mao_de_obra, valor_total, status, data_abertura
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (cliente_id, descricao_problema, tipo_servico, valor_material, valor_mao_de_obra, valor_total, status, data_abertura),
    )
    ordem_id = cursor.lastrowid
    if servicos:
        for item in servicos:
            conn.execute(
                'INSERT INTO ordem_servico_itens (ordem_id, servico, quantidade, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?)',
                (ordem_id, item['nome'], item['quantidade'], item['valor'], item['valor_total'])
            )
    conn.commit()
    conn.close()
    return ordem_id


def buscar_cliente_por_id(cliente_id):
    conn = get_connection()
    cliente = conn.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
    conn.close()
    return cliente


def buscar_ordem_por_id(ordem_id):
    conn = get_connection()
    ordem = conn.execute('SELECT * FROM ordens_servico WHERE id = ?', (ordem_id,)).fetchone()
    conn.close()
    return ordem


def buscar_itens_ordem(ordem_id):
    conn = get_connection()
    itens = conn.execute('SELECT * FROM ordem_servico_itens WHERE ordem_id = ? ORDER BY id', (ordem_id,)).fetchall()
    conn.close()
    return itens


def atualizar_ordem(ordem_id, cliente_id, descricao_problema, tipo_servico, valor_material, valor_mao_de_obra, status, servicos=None):
    valor_total = float(valor_material) + float(valor_mao_de_obra)
    conn = get_connection()
    conn.execute(
        '''
        UPDATE ordens_servico
        SET cliente_id = ?, descricao_problema = ?, tipo_servico = ?, valor_material = ?,
            valor_mao_de_obra = ?, valor_total = ?, status = ?
        WHERE id = ?
        ''',
        (cliente_id, descricao_problema, tipo_servico, valor_material, valor_mao_de_obra, valor_total, status, ordem_id),
    )
    conn.execute('DELETE FROM ordem_servico_itens WHERE ordem_id = ?', (ordem_id,))
    if servicos:
        for item in servicos:
            conn.execute(
                'INSERT INTO ordem_servico_itens (ordem_id, servico, quantidade, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?)',
                (ordem_id, item['nome'], item['quantidade'], item['valor'], item['valor_total'])
            )
    conn.commit()
    conn.close()


def excluir_ordem(ordem_id):
    conn = get_connection()
    conn.execute('DELETE FROM ordens_servico WHERE id = ?', (ordem_id,))
    conn.commit()
    conn.close()
