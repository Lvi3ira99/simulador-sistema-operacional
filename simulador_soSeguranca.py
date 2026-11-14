import math
import hashlib
import os

# =====================================================================
# CAMADA DE SEGURANÇA: IDENTIDADE, ACL, CRIPTOGRAFIA E INTEGRIDADE
# =====================================================================
class SecurityManager:
    """Gerencia Usuários, Autenticação, Modos de Execução e Criptografia"""
    def __init__(self):
        # Banco de dados de usuários simulado (Senhas com Salt + SHA-256)
        self.users = {}
        self.current_user = None
        self.current_group = None
        self.mode = "MODO_USUARIO"
        
        # Registra usuários padrão (root e carlos)
        self._register_user("root", "admin", "root123")
        self._register_user("carlos", "devs", "senha123")

    def _register_user(self, username, group, password):
        salt = os.urandom(16).hex()
        pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        self.users[username] = {"group": group, "salt": salt, "hash": pwd_hash}

    def login(self, username, password):
        if username not in self.users:
            return False
        
        user_data = self.users[username]
        attempt_hash = hashlib.sha256((user_data["salt"] + password).encode()).hexdigest()
        
        if attempt_hash == user_data["hash"]:
            self.current_user = username
            self.current_group = user_data["group"]
            self.mode = "MODO_KERNEL" if username == "root" else "MODO_USUARIO"
            return True
        return False

    def logout(self):
        self.current_user = None
        self.current_group = None
        self.mode = "MODO_USUARIO"

    def check_permission(self, node, action, action_type):
        """
        Valida matriz de acesso rwx. action: 0(r), 1(w), 2(x)
        action_type: "LEITURA", "ESCRITA", "EXECUCAO"
        """
        if self.mode == "MODO_KERNEL" or self.current_user == "root":
            return True # Root tem poder absoluto
            
        # Pega a string de permissão, ex: 'rwxr-x---' -> owner: rwx, group: r-x, others: ---
        perms = node.permissions
        owner_perms = perms[0:3]
        group_perms = perms[3:6]
        other_perms = perms[6:9]
        
        if self.current_user == node.owner:
            allowed = owner_perms[action] != '-'
        elif self.current_group == node.group:
            allowed = group_perms[action] != '-'
        else:
            allowed = other_perms[action] != '-'

        if not allowed:
            # Formatação de string rwx para numérico (ex: rwxr-x--- -> 750)
            def rwx_to_octal(rwx):
                return str((4 if rwx[0]=='r' else 0) + (2 if rwx[1]=='w' else 0) + (1 if rwx[2]=='x' else 0))
            octal_perms = rwx_to_octal(owner_perms) + rwx_to_octal(group_perms) + rwx_to_octal(other_perms)

            print(f"\n[SISTEMA DE SEGURANÇA - VERIFICAÇÃO DE ACL]")
            print(f"Objeto      : {node.full_path}")
            print(f"Proprietário: {node.owner} (Grupo: {node.group})")
            print(f"Permissões  : {node.permissions} ({octal_perms})")
            print(f"Ação Pedida : {action_type} por '{self.current_user}' (Grupo: {self.current_group})\n")
            print(f"[NEGADO]: O usuário '{self.current_user}' não possui permissão de {action_type.lower()} no objeto '{node.full_path}'.")
            print("Tentativa não autorizada registrada nos logs do sistema.\n")
            return False
            
        return True

    def encrypt_data(self, data, key):
        """Simula criptografia gerando um Ciphertext"""
        # Apenas simulação visual para o simulador
        cipher = hashlib.md5((data + key).encode()).hexdigest()[:10].upper()
        return f"0x{cipher}... (Encrypted Ciphertext)"

    def generate_integrity_hash(self, data):
        return hashlib.sha256(data.encode()).hexdigest()

# =====================================================================
# CAMADA FÍSICA: DISCO LÓGICO, ESCALONAMENTO E RAID 5 (MANTIDOS)
# =====================================================================
class Disk:
    def __init__(self, total_blocks=32, block_size=4096):
        self.total_blocks = total_blocks
        self.block_size = block_size
        self.free_count = total_blocks
        self.blocks = [{"type": "LIVRE", "info": "", "data_raw": ""} for _ in range(total_blocks)]

    def allocate_blocks(self, count):
        if count > self.free_count: return None 
        allocated = []
        for i in range(self.total_blocks):
            if self.blocks[i]["type"] == "LIVRE":
                allocated.append(i)
                if len(allocated) == count: break
        self.free_count -= len(allocated)
        return allocated

class DiskScheduler:
    def __init__(self, current_head_position=15):
        self.head_position = current_head_position

    def schedule_sstf(self, requests_queue):
        if not requests_queue: return
        pending = list(requests_queue)
        current_pos = self.head_position
        while pending:
            closest_track = min(pending, key=lambda track: abs(track - current_pos))
            current_pos = closest_track
            pending.remove(closest_track)
        self.head_position = current_pos

class RAID5Controller:
    def __init__(self, num_disks=3):
        self.num_disks = num_disks
        self.physical_disks = {1: {}, 2: {}, 3: {}}

    def write_data(self, filename, data_blocks):
        for stripe_idx, i in enumerate(range(0, len(data_blocks), 2)):
            b1 = data_blocks[i]
            b2 = data_blocks[i+1] if i+1 < len(data_blocks) else "NULO"
            parity_disk = 3 - (stripe_idx % 3)
            data_disks = [d for d in [1, 2, 3] if d != parity_disk]
            self.physical_disks[data_disks[0]][b1] = f"Dado {filename}"
            self.physical_disks[data_disks[1]][b2] = f"Dado {filename}"
            self.physical_disks[parity_disk][f"P({b1},{b2})"] = f"XOR({b1},{b2})"

# =====================================================================
# CAMADA LÓGICA: SISTEMA DE ARQUIVOS (COM SEGURANÇA INTEGRADA)
# =====================================================================
class Node:
    """Representa um Arquivo ou Diretório com Atributos de Segurança"""
    def __init__(self, name, is_dir, parent=None, size_bytes=0, owner="root", group="admin", perms="rwxr-xr-x"):
        self.name = name
        self.is_dir = is_dir
        self.parent = parent
        self.children = {}
        self.size_bytes = size_bytes
        self.inode_block = None
        self.data_blocks = []
        
        # Atributos de Segurança e Identidade
        self.owner = owner
        self.group = group
        self.permissions = perms # Ex: 'rwxr-x---'
        self.is_encrypted = False
        self.integrity_hash = None # Assinatura para o Anti-Virus
        self.full_path = self._build_path()

    def _build_path(self):
        if self.parent is None: return "/"
        if self.parent.name == "/": return "/" + self.name
        return self.parent.full_path + "/" + self.name

class FileSystem:
    def chmod(self, path, perms):
        """Altera as permissões de um arquivo ou diretório"""
        node, _, _ = self._resolve_path(path)
        if not node: 
            return print(f"Erro: Caminho '{path}' não encontrado.")
            
        # Apenas root ou o dono do arquivo podem mudar a permissão
        if self.security.current_user != node.owner and self.security.mode != "MODO_KERNEL":
            return print(f"[NEGADO]: Apenas o proprietário ({node.owner}) ou root podem alterar as permissões.")
            
        if len(perms) != 9:
            return print("Erro: Formato inválido. Use 9 caracteres (ex: rwxr-xr-x ou rw-r-----)")
            
        node.permissions = perms
        print(f"Permissões de '{path}' atualizadas para {perms}.")
    def __init__(self):
        self.security = SecurityManager()
        self.disk = Disk(total_blocks=32, block_size=4096)
        self.scheduler = DiskScheduler()
        self.raid = RAID5Controller()
        
        self.root = Node("/", is_dir=True, owner="root", group="admin", perms="rwxr-xr-x")
        self.disk.allocate_blocks(1)
        
        # Pre-popula um arquivo de sistema para teste de permissão
        self._create_system_file()

    def _create_system_file(self):
        # Cria a pasta /sistema e o arquivo config.sys bloqueado
        sys_dir = Node("sistema", is_dir=True, parent=self.root, owner="root", group="admin", perms="rwxr-xr-x")
        self.root.children["sistema"] = sys_dir
        
        config = Node("config.sys", is_dir=False, parent=sys_dir, size_bytes=1024, owner="root", group="admin", perms="rwxr-x---")
        config.data_blocks = self.disk.allocate_blocks(2)[1:]
        
        # Simula gravação de dados
        raw_data = "CONFIGURACAO_CRITICA_DO_SISTEMA"
        config.integrity_hash = self.security.generate_integrity_hash(raw_data)
        for b in config.data_blocks:
            self.disk.blocks[b]["data_raw"] = raw_data
            
        sys_dir.children["config.sys"] = config

    def _resolve_path(self, path):
        if path == "/" or not path: return self.root, None, None
        curr = self.root
        parts = [p for p in path.split("/") if p]
        for part in parts[:-1]:
            if part in curr.children and curr.children[part].is_dir:
                curr = curr.children[part]
            else:
                return None, None, None
        target = parts[-1]
        if target in curr.children: return curr.children[target], target, curr
        else: return None, target, curr

    def mkdir(self, path):
        if not self.security.current_user:
            print("Erro: Sessão não autenticada.")
            return
            
        node, missing, parent = self._resolve_path(path)
        if parent is None: return print(f"Erro: Caminho base não existe.")
        if node: return print(f"Erro: O diretório '{path}' já existe.")
        
        # Checa permissão de ESCRITA (1) no diretório pai
        if not self.security.check_permission(parent, 1, "ESCRITA"): return
            
        new_dir = Node(missing, is_dir=True, parent=parent, 
                       owner=self.security.current_user, 
                       group=self.security.current_group, 
                       perms="rwxr-xr-x")
        parent.children[missing] = new_dir
        print(f"> Diretório '{path}' criado com sucesso.")

    def create_file(self, path, data_content):
        if not self.security.current_user:
            return print("Erro: Sessão não autenticada. Faça login primeiro.")
            
        node, missing, parent = self._resolve_path(path)
        if parent is None: return print(f"Erro: Caminho base inválido.")
        if node: return print(f"Erro: O arquivo já existe.")
        if not self.security.check_permission(parent, 1, "ESCRITA"): return
        
        size_bytes = len(data_content.encode('utf-8'))
        data_blocks_needed = max(1, math.ceil(size_bytes / self.disk.block_size))
        blocks = self.disk.allocate_blocks(data_blocks_needed + 1)
        
        if not blocks: return print("Erro: Espaço insuficiente.")

        # Por padrão, um usuário normal cria arquivo restrito a ele e leitura pro grupo (640 = rw-r-----)
        perms = "rw-r-----" if self.security.current_user != "root" else "rwxr-xr-x"
        
        new_file = Node(missing, is_dir=False, parent=parent, size_bytes=size_bytes,
                        owner=self.security.current_user, group=self.security.current_group, perms=perms)
        new_file.inode_block = blocks[0]
        new_file.data_blocks = blocks[1:]
        
        # Salva o Hash de Integridade Original
        new_file.integrity_hash = self.security.generate_integrity_hash(data_content)
        
        for b_idx in new_file.data_blocks:
            self.disk.blocks[b_idx] = {"type": "[DADO]", "info": f"'{path}'", "data_raw": data_content}

        parent.children[missing] = new_file
        self.scheduler.schedule_sstf(new_file.data_blocks)
        self.raid.write_data(missing, new_file.data_blocks)
        print(f"\n> Arquivo '{path}' criado por '{self.security.current_user}'. Integridade Hash registrada.")

    def read_file(self, path):
        node, _, _ = self._resolve_path(path)
        if not node or node.is_dir:
            return print(f"Erro: Arquivo '{path}' não encontrado.")
            
        # Checa permissão de LEITURA (0)
        if not self.security.check_permission(node, 0, "LEITURA"): return
        
        print(f"\nLendo conteúdo de {path}...")
        for b_idx in node.data_blocks:
            data = self.disk.blocks[b_idx]["data_raw"]
            print(f"[Bloco {b_idx}]: {data}")

    def encrypt_file(self, path, key):
        node, _, _ = self._resolve_path(path)
        if not node or node.is_dir: return print(f"Erro: Arquivo não encontrado.")
        if not self.security.check_permission(node, 1, "ESCRITA"): return
        
        if node.is_encrypted:
            return print("Arquivo já está criptografado.")

        print(f"Criptografando '{path}' com AES-256 (Simulado)...")
        for b_idx in node.data_blocks:
            raw = self.disk.blocks[b_idx]["data_raw"]
            cipher = self.security.encrypt_data(raw, key)
            self.disk.blocks[b_idx]["data_raw"] = cipher # Substitui o bloco físico
            
        node.is_encrypted = True
        # Atualiza o hash de integridade para refletir o texto cifrado
        new_combined_data = "".join([self.disk.blocks[b]["data_raw"] for b in node.data_blocks])
        node.integrity_hash = self.security.generate_integrity_hash(new_combined_data)
        
        print(f"Arquivo '{path}' criptografado com sucesso.")
        print(f"Conteúdo gravado nos blocos físicos: \"{self.disk.blocks[node.data_blocks[0]]['data_raw']}\"")

    def antivirus_scan(self):
        print("\n[MÓDULO DE SEGURANÇA - VARREDURA DE INTEGRIDADE]")
        print("Analisando arquivos em busca de assinaturas maliciosas e hashes corrompidos...\n")
        
        files_scanned = 0
        def scan_node(n):
            nonlocal files_scanned
            if not n.is_dir:
                files_scanned += 1
                # Reconstrói os dados do disco físico
                current_data = "".join([self.disk.blocks[b]["data_raw"] for b in n.data_blocks])
                current_hash = self.security.generate_integrity_hash(current_data)
                
                status_crypto = "Criptografado e " if n.is_encrypted else ""
                
                if current_hash == n.integrity_hash:
                    print(f"- {n.full_path:<30}: [OK - {status_crypto}Íntegro]")
                else:
                    print(f"- {n.full_path:<30}: [ALERTA] Hash do bloco difere do registro oficial!")
                    print("   >> Resultado: Possível modificação direta não autorizada no bloco do disco.\n")
                    
            for child in n.children.values():
                scan_node(child)

        scan_node(self.root)
        print(f"\nVarredura concluída: {files_scanned} arquivo(s) analisado(s).")

    def corrupt_file_for_test(self, path):
        """Simula a invasão de um hacker alterando fisicamente o disco (Bypass do FS)"""
        node, _, _ = self._resolve_path(path)
        if node and not node.is_dir and node.data_blocks:
            # Altera diretamente o setor físico ignorando a arvore lógica
            self.disk.blocks[node.data_blocks[0]]["data_raw"] = "###PAYLOAD_MALICIOSO###"
            print(f"[!] HACK SIMULADO: Bloco físico do arquivo '{path}' adulterado por fora do Sistema de Arquivos.")

# =====================================================================
# CLI - INTERAÇÃO COM O USUÁRIO
# =====================================================================
if __name__ == "__main__":
    fs = FileSystem()
    print("🔐 Login no Sistema Operacional 🔐")
    print("Usuários padrão disponíveis para teste:")
    print(" 1) root   (senha: root123)")
    print(" 2) carlos (senha: senha123)")
   
while True:
        try:
            prompt = f"{fs.security.current_user or 'visitante'}@simulador> "
            entrada = input(f"\n{prompt}").strip().split()
            if not entrada: continue
                
            comando = entrada[0].lower()
            
            if comando == "sair":
                break
                
            elif comando == "login" and len(entrada) >= 3 and entrada[1] == "--user":
                user = entrada[2]
                pwd = input(f"Senha para {user}: ")
                if fs.security.login(user, pwd):
                    print(f"Autenticado com sucesso. Usuário: '{user}' | Grupo: '{fs.security.current_group}' | Modo: {fs.security.mode}")
                    print("\n                  💻 BEM VINDO AO SISTEMA OPERACIONAL 💻")
                    print("\nComandos disponíveis:")
                    print("  login --user <nome>                    - Autentica no sistema")
                    print("  logout                                 - Encerra sessão")
                    print("  useradd <nome> <grupo> <senha>         - Cria novo usuário (Apenas Root)")
                    print("  chmod <caminho> <perm>                 - Altera permissões (Ex: rwxrwxrwx)")
                    print("  mkdir <caminho>                        - Cria diretório")
                    print("  create_file <caminho> <conteudo_texto> - Cria arquivo com conteúdo")
                    print("  read_file <caminho>                    - Lê conteúdo (checa ACL)")
                    print("  encrypt_file <caminho> --key <chave>   - Criptografa arquivo")
                    print("  antivirus_scan /                       - Varredura de integridade (Hash)")
                    print("  hack_disk <caminho>                    - (Teste) Modifica bloco físico")
                    print("  ajuda                                  - Exibe este menu novamente")
                    print("  sair                                   - Encerra o simulador\n")
                    print("Qual opção deseja escolher?\nInsira o comando correspondente:")                            
                else:
                    print("Falha na autenticação.")
            elif comando == "useradd" and len(entrada) == 4:
                # Exemplo: useradd alice testers alice123
                if fs.security.mode == "MODO_KERNEL":
                    fs.security._register_user(entrada[1], entrada[2], entrada[3])
                    print(f"Usuário '{entrada[1]}' (Grupo: {entrada[2]}) criado com sucesso no banco de dados.")
                else:
                    print("[NEGADO]: Operação restrita. Apenas usuários com permissão de Admin ou root podem criar usuários.")

            elif comando == "chmod" and len(entrada) == 3:
                # Exemplo: chmod /docs/texto.txt rwxrwxrwx
                fs.chmod(entrada[1], entrada[2])

            elif comando == "logout":
                fs.security.logout()
                print("Sessão encerrada.")

            elif comando == "mkdir" and len(entrada) == 2:
                fs.mkdir(entrada[1])
                
            elif comando == "create_file" and len(entrada) >= 3:
                # Exemplo: create_file /docs/texto.txt Meu_conteudo_secreto
                content = " ".join(entrada[2:])
                fs.create_file(entrada[1], content)
                
            elif comando == "read_file" and len(entrada) == 2:
                fs.read_file(entrada[1])
                
            elif comando == "encrypt_file" and len(entrada) >= 4 and entrada[2] == "--key":
                # Exemplo: encrypt_file /docs/texto.txt --key MinhaChave123
                fs.encrypt_file(entrada[1], entrada[3])
                
            elif comando == "antivirus_scan":
                # Executa na raiz por padrão
                fs.antivirus_scan()
                
            elif comando == "hack_disk" and len(entrada) == 2:
                # Comando secreto para corromper o arquivo e testar o AV
                fs.corrupt_file_for_test(entrada[1])
            elif comando == "ajuda":
                print("📝Para realizar login, você deve usar o comando: login --user <nome>")
            else:
                print("⚠️  Comando inválido ou incompleto. Digite 'ajuda'")
        except Exception as e:
            print(f"Erro inesperado: {e}")