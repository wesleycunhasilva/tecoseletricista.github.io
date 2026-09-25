import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get('TECOS_DB_PATH', str(Path(__file__).resolve().parent / 'tecos.db')))
if DB_PATH.parent != Path('.') and not DB_PATH.parent.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
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
    conn.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            bio TEXT NOT NULL DEFAULT '',
            avatar_url TEXT,
            github_url TEXT,
            linkedin_url TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS technologies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            icon_url TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            repository_url TEXT,
            demo_url TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS project_technologies (
            project_id INTEGER NOT NULL,
            technology_id INTEGER NOT NULL,
            PRIMARY KEY (project_id, technology_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (technology_id) REFERENCES technologies(id) ON DELETE CASCADE
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            rating INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
        )
    ''')
    conn.commit()
    conn.close()


def _row_to_dict(row):
    return dict(row) if row else None


def criar_profile(dados):
    conn = get_connection()
    cursor = conn.execute(
        '''INSERT INTO profiles (name, bio, avatar_url, github_url, linkedin_url)
           VALUES (?, ?, ?, ?, ?)''',
        (dados['name'], dados.get('bio', ''), dados.get('avatar_url'), dados.get('github_url'), dados.get('linkedin_url')),
    )
    conn.commit()
    profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return _row_to_dict(profile)


def buscar_profile(profile_id):
    conn = get_connection()
    profile = conn.execute('SELECT * FROM profiles WHERE id = ?', (profile_id,)).fetchone()
    if profile:
        profile = _row_to_dict(profile)
        profile['projects'] = [
            _row_to_dict(row) for row in conn.execute(
                'SELECT * FROM projects WHERE profile_id = ? ORDER BY id DESC', (profile_id,)
            ).fetchall()
        ]
    conn.close()
    return profile


def criar_technology(dados):
    conn = get_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO technologies (name, description, icon_url) VALUES (?, ?, ?)',
            (dados['name'], dados.get('description', ''), dados.get('icon_url')),
        )
        conn.commit()
        technology = conn.execute('SELECT * FROM technologies WHERE id = ?', (cursor.lastrowid,)).fetchone()
        return _row_to_dict(technology)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_technologies():
    conn = get_connection()
    technologies = [_row_to_dict(row) for row in conn.execute('SELECT * FROM technologies ORDER BY name').fetchall()]
    conn.close()
    return technologies


def criar_project(dados):
    conn = get_connection()
    cursor = conn.execute(
        '''INSERT INTO projects (profile_id, title, description, repository_url, demo_url)
           VALUES (?, ?, ?, ?, ?)''',
        (dados['profile_id'], dados['title'], dados.get('description', ''), dados.get('repository_url'), dados.get('demo_url')),
    )
    project_id = cursor.lastrowid
    conn.executemany(
        'INSERT INTO project_technologies (project_id, technology_id) VALUES (?, ?)',
        [(project_id, technology_id) for technology_id in dados.get('technology_ids', [])],
    )
    conn.commit()
    project = _project_with_relations(conn, project_id)
    conn.close()
    return project


def _project_with_relations(conn, project_id):
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return None
    result = _row_to_dict(project)
    result['technologies'] = [
        _row_to_dict(row) for row in conn.execute(
            '''SELECT t.* FROM technologies t
               INNER JOIN project_technologies pt ON pt.technology_id = t.id
               WHERE pt.project_id = ? ORDER BY t.name''', (project_id,)
        ).fetchall()
    ]
    result['feedbacks'] = [
        _row_to_dict(row) for row in conn.execute(
            'SELECT * FROM feedbacks WHERE project_id = ? ORDER BY id DESC', (project_id,)
        ).fetchall()
    ]
    return result


def listar_projects():
    conn = get_connection()
    projects = [_project_with_relations(conn, row['id']) for row in conn.execute('SELECT id FROM projects ORDER BY id DESC').fetchall()]
    conn.close()
    return projects


def criar_feedback(project_id, dados):
    conn = get_connection()
    cursor = conn.execute(
        'INSERT INTO feedbacks (project_id, author_name, content, rating) VALUES (?, ?, ?, ?)',
        (project_id, dados['author_name'], dados['content'], dados.get('rating')),
    )
    conn.commit()
    feedback = conn.execute('SELECT * FROM feedbacks WHERE id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return _row_to_dict(feedback)


def profile_existe(profile_id):
    conn = get_connection()
    exists = conn.execute('SELECT 1 FROM profiles WHERE id = ?', (profile_id,)).fetchone() is not None
    conn.close()
    return exists


def technologies_existem(technology_ids):
    conn = get_connection()
    placeholders = ','.join('?' for _ in technology_ids)
    count = conn.execute(f'SELECT COUNT(*) AS total FROM technologies WHERE id IN ({placeholders})', technology_ids).fetchone()['total']
    conn.close()
    return count == len(set(technology_ids))


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
