import math
import hashlib
import os
import sys
import time
import re

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
# CAMADA DE MEMÓRIA: ALOCAÇÃO HÍBRIDA, PAGINAÇÃO, SWAP E COMPACTAÇÃO
# =====================================================================
class Process:
    """Representa um processo no SO (Crítico na RAM Reservada ou Normal na Memória Virtual)"""
    def __init__(self, pid, name, size_bytes, proc_type, owner="root"):
        self.pid = pid
        self.name = name
        self.size_bytes = size_bytes
        self.proc_type = proc_type  # "critical" ou "normal"
        self.owner = owner
        self.page_table = {}        # {page_num: {"present": bool, "frame": int|None, "in_swap": bool, "used_bytes": int}}
        self.internal_fragmentation_bytes = 0

class ReservedMemoryManager:
    """Gerencia a Área Estática/Fixa (Reservada) da RAM com Alocação Contígua (4 MB)"""
    def __init__(self, total_kb=4096):
        self.total_kb = total_kb
        self.segments = [
            {"start_kb": 0, "size_kb": 1024, "process": "Núcleo Base do SO", "protected": True},
            {"start_kb": 1024, "size_kb": total_kb - 1024, "process": None, "protected": False}
        ]

    @staticmethod
    def _fmt_mb(kb):
        mb = kb / 1024.0
        if round(mb * 10) == mb * 10:
            return f"{mb:.1f} MB"
        return f"{mb:.2f} MB"

    def _coalesce_free_segments(self):
        """Mescla blocos livres adjacentes para evitar falsos fragmentos"""
        merged = []
        for seg in self.segments:
            if merged and merged[-1]["process"] is None and seg["process"] is None:
                merged[-1]["size_kb"] += seg["size_kb"]
            else:
                merged.append(seg)
        self.segments = merged

    def allocate(self, process_name, size_kb):
        """Aloca espaço contíguo (First-Fit) na Área Reservada"""
        if size_kb <= 0:
            print("Erro: Tamanho do processo deve ser maior que zero.")
            return False

        for idx, seg in enumerate(self.segments):
            if seg["process"] is None and seg["size_kb"] >= size_kb:
                start_kb = seg["start_kb"]
                end_kb = start_kb + size_kb
                remaining = seg["size_kb"] - size_kb

                allocated_seg = {
                    "start_kb": start_kb,
                    "size_kb": size_kb,
                    "process": process_name,
                    "protected": False
                }

                if remaining > 0:
                    free_remainder = {
                        "start_kb": end_kb,
                        "size_kb": remaining,
                        "process": None,
                        "protected": False
                    }
                    self.segments[idx:idx+1] = [allocated_seg, free_remainder]
                else:
                    self.segments[idx] = allocated_seg

                print(f"\n[ALOCAÇÃO CONCLUÍDA] Processo '{process_name}' devidamente alocado de forma contígua na Área Reservada: [{self._fmt_mb(start_kb)} até {self._fmt_mb(end_kb)}] ({size_kb} KB).")
                return True

        free_segs = [s for s in self.segments if s["process"] is None]
        total_free = sum(s["size_kb"] for s in free_segs)
        max_free = max((s["size_kb"] for s in free_segs), default=0)

        if total_free >= size_kb:
            print(f"[FALHA DE ALOCAÇÃO - FRAGMENTAÇÃO EXTERNA]: Não há bloco contíguo único de {size_kb} KB.")
            print(f"Memória livre total: {total_free} KB | Maior bloco contíguo: {max_free} KB.")
            print("Use a opção de compactação da Área Reservada e tente novamente.")
        else:
            print(f"[ERRO]: Memória insuficiente na Área Reservada. Livre: {total_free} KB | Requisitado: {size_kb} KB.")
        return False

    def deallocate(self, process_name):
        """Libera o bloco contíguo ocupado por um processo crítico"""
        for seg in self.segments:
            if seg["process"] == process_name:
                if seg["protected"]:
                    print(f"[NEGADO]: '{process_name}' é protegido e não pode ser encerrado.")
                    return False
                start_kb = seg["start_kb"]
                end_kb = start_kb + seg["size_kb"]
                freed_kb = seg["size_kb"]
                seg["process"] = None
                self._coalesce_free_segments()

                print(f"[ENCERRAMENTO DE PROCESSO CRÍTICO] Processo '{process_name}' finalizado.")
                print(f"Área de {freed_kb} KB no intervalo [{self._fmt_mb(start_kb)} a {self._fmt_mb(end_kb)}] liberada na Área Reservada da RAM.")
                return True
        return False

    def get_metrics(self):
        free_segs = [s for s in self.segments if s["process"] is None]
        used_kb = sum(s["size_kb"] for s in self.segments if s["process"] is not None)
        total_free = sum(s["size_kb"] for s in free_segs)
        max_free = max((s["size_kb"] for s in free_segs), default=0)
        has_ext_frag = len(free_segs) > 1
        return {
            "total_kb": self.total_kb,
            "used_kb": used_kb,
            "free_kb": total_free,
            "max_contiguous_kb": max_free,
            "free_fragments": len(free_segs),
            "has_external_fragmentation": has_ext_frag
        }

    def _print_map(self):
        free_segs_count = sum(1 for s in self.segments if s["process"] is None)
        frag_idx = 0
        for seg in self.segments:
            start_kb = seg["start_kb"]
            end_kb = start_kb + seg["size_kb"]
            interval = f"[{self._fmt_mb(start_kb)} - {self._fmt_mb(end_kb)}]"
            size_str = f"({seg['size_kb']} KB)"

            if seg["process"] is not None:
                label = seg["process"]
                tag = "[OCUPADO]"
            else:
                if free_segs_count > 1:
                    frag_idx += 1
                    label = f"FRAGMENTO LIVRE {frag_idx}"
                    tag = "[LIVRE - LACUNA]"
                else:
                    label = "Bloco Livre Contíguo"
                    tag = "[LIVRE]"

            print(f"{interval:<18}: {label:<21} {size_str:<10} {tag}")

    def print_status(self):
        total_mb_str = f"{int(self.total_kb / 1024)} MB" if self.total_kb % 1024 == 0 else self._fmt_mb(self.total_kb)
        print(f"--- MAPA DA ÁREA CRÍTICA/RESERVADA DA RAM (Total: {total_mb_str} - Alocação Fixa) ---")
        self._print_map()

        metrics = self.get_metrics()
        total_free = metrics["free_kb"]
        max_free = metrics["max_contiguous_kb"]
        frags = metrics["free_fragments"]

        print("\n--- DIAGNÓSTICO DE FRAGMENTAÇÃO EXTERNA ---")
        print(f"Total de Memória Livre na Área Reservada : {total_free} KB ({self._fmt_mb(total_free)})")
        print(f"Maior Bloco Contíguo Disponível          : {max_free} KB ({self._fmt_mb(max_free)})")

        if metrics["has_external_fragmentation"]:
            print(f"Fragmentação Externa Detectada           : SIM ({frags} fragmentos não contíguos)")
            sample_req = (max_free + total_free) // 2
            print(f"Status: Uma requisição contígua de {sample_req} KB falhará por ausência de bloco único.")
        else:
            print("Fragmentação Externa Detectada           : NÃO (Espaço livre contíguo)")
            print(f"Status: Área reservada otimizada. Requisições contíguas de até {max_free} KB são atendidas.")

    def compact(self):
        """Realoca todos os processos ocupados contiguamente eliminando lacunas"""
        metrics = self.get_metrics()
        occupied = [s for s in self.segments if s["process"] is not None]

        needs_compaction = metrics["has_external_fragmentation"] or (
            len(self.segments) > 1 and self.segments[-1]["process"] is not None and metrics["free_kb"] > 0
        )

        print("[EXECUTANDO COMPACTAÇÃO DA ÁREA RESERVADA DA RAM]")
        if not needs_compaction:
            print("A Área Reservada já está compactada. Nenhuma realocação necessária.")
            return

        print("Realocando blocos contíguos para eliminar a fragmentação externa...")
        new_segments = []
        cursor = 0

        for seg in occupied:
            old_start = seg["start_kb"]
            old_end = old_start + seg["size_kb"]
            new_start = cursor
            new_end = cursor + seg["size_kb"]

            if new_start != old_start:
                print(
                    f"- Mapeamento de '{seg['process']}': "
                    f"[{self._fmt_mb(old_start)} a {self._fmt_mb(old_end)}] -> "
                    f"Ajustado para: [{self._fmt_mb(new_start)} a {self._fmt_mb(new_end)}]"
                )

            new_segments.append({
                "start_kb": new_start,
                "size_kb": seg["size_kb"],
                "process": seg["process"],
                "protected": seg["protected"]
            })
            cursor = new_end

        free_kb = self.total_kb - cursor
        if free_kb > 0:
            new_segments.append({
                "start_kb": cursor,
                "size_kb": free_kb,
                "process": None,
                "protected": False
            })

        self.segments = new_segments

        print("\n--- MAPA APÓS COMPACTAÇÃO ---")
        self._print_map()
        print(f"Resultado: Fragmentação externa eliminada. Maior bloco contíguo: {free_kb} KB.")


class VirtualMemoryManager:
    """Gerencia a Área Dinâmica (Paginação), Tradução, Page Faults, Swap e Substituição"""
    def __init__(self, num_frames=4, page_size=4096, policy="LRU"):
        self.num_frames = num_frames
        self.page_size = page_size
        self.policy = policy.upper()  # "LRU", "SECOND_CHANCE", "FIFO"
        self.frames = [None for _ in range(num_frames)]
        self.swap_space = {}          # {(pid, page_num): {"process_name": str, "saved_at": float}}
        self.clock_hand = 0
        self.page_faults = 0
        self.page_hits = 0
        self.swap_outs = 0

    def set_policy(self, policy):
        valid = {"LRU", "SECOND_CHANCE", "FIFO"}
        p = policy.upper()
        if p not in valid:
            print(f"Erro: Política '{policy}' inválida. Use: LRU, SECOND_CHANCE ou FIFO.")
            return False
        self.policy = p
        print(f"Algoritmo de substituição de páginas alterado para: {self.policy}")
        return True

    def register_process(self, process):
        """Gera a Tabela de Páginas sob demanda e calcula a fragmentação interna (sem exibir detalhes)"""
        size_bytes = process.size_bytes
        num_pages = max(1, math.ceil(size_bytes / self.page_size))

        remaining = size_bytes
        total_waste = 0
        for p in range(num_pages):
            used = min(self.page_size, remaining)
            remaining -= used
            waste = self.page_size - used
            total_waste += waste
            process.page_table[p] = {
                "present": False,
                "frame": None,
                "in_swap": False,
                "used_bytes": used
            }

        process.internal_fragmentation_bytes = total_waste

    def print_page_calculation(self, process):
        """Exibe somente o cálculo de páginas do processo"""
        size_bytes = process.size_bytes
        size_kb = size_bytes / 1024.0
        size_kb_str = f"{int(size_kb)}" if size_kb.is_integer() else f"{size_kb:.2f}"
        page_kb = self.page_size // 1024

        num_pages = len(process.page_table)
        ratio = size_bytes / self.page_size
        ratio_str = f"{int(ratio)}" if ratio.is_integer() else f"{ratio:.2f}".rstrip('0').rstrip('.')

        if num_pages == 1:
            pages_desc = "Página 0"
        elif num_pages == 2:
            pages_desc = "Páginas 0 e 1"
        else:
            pages_desc = "Páginas " + ", ".join(str(i) for i in range(num_pages - 1)) + f" e {num_pages - 1}"

        print("\n--- CÁLCULO DE PÁGINAS (MEMÓRIA VIRTUAL) ---")
        print(f"Processo            : {process.name} (PID {process.pid})")
        print(f"Tamanho do Processo : {size_kb_str} KB ({size_bytes} Bytes)")
        print(f"Tamanho da Página   : {page_kb} KB ({self.page_size} Bytes)")
        print(f"Cálculo de Páginas  : {size_kb_str} KB / {page_kb} KB = {ratio_str} -> Requer {num_pages} Página(s) Lógica(s) ({pages_desc}).")
        print("Status: Tabela de Páginas gerada sem alocar molduras na RAM (Alocação por demanda).")

    def print_internal_fragmentation(self, process):
        """Exibe somente a análise de fragmentação interna do processo"""
        num_pages = len(process.page_table)
        total_waste = process.internal_fragmentation_bytes

        print("\n--- ANÁLISE DE FRAGMENTAÇÃO INTERNA ---")
        for p in range(num_pages):
            used = process.page_table[p]["used_bytes"]
            pct = (used / self.page_size) * 100
            pct_str = f"{int(pct)}%" if pct.is_integer() else f"{pct:.1f}%"
            if used == self.page_size:
                print(f"Página Lógica {p} : {used} Bytes ocupados ({pct_str})")
            else:
                print(f"Página Lógica {p} : {used} Bytes ocupados ({pct_str} de uso)")

        if total_waste > 0:
            print(f"Fragmentação Interna Total: {total_waste} Bytes de desperdício na Página Lógica {num_pages - 1}.")
        else:
            print("Fragmentação Interna Total: 0 Bytes de desperdício (alinhamento exato com o tamanho da página).")

    def preload_page(self, process, page_num, age_ms=0, ref_bit=1):
        """Usado no boot para simular processos em segundo plano ocupando molduras na RAM Dinâmica"""
        for f_idx in range(self.num_frames):
            if self.frames[f_idx] is None:
                now = time.perf_counter()
                ts = now - (age_ms / 1000.0)
                self.frames[f_idx] = {
                    "pid": process.pid,
                    "process": process,
                    "page_num": page_num,
                    "loaded_at": ts,
                    "last_access": ts,
                    "ref_bit": ref_bit
                }
                process.page_table[page_num]["present"] = True
                process.page_table[page_num]["frame"] = f_idx
                return f_idx
        return None

    def release_process(self, process):
        """Libera molduras na RAM Dinâmica e entradas no Swap de um processo encerrado"""
        freed_frames = []
        for f_idx, frame in enumerate(self.frames):
            if frame and frame["pid"] == process.pid:
                self.frames[f_idx] = None
                freed_frames.append(f_idx)

        removed_swap = [key for key in self.swap_space if key[0] == process.pid]
        for key in removed_swap:
            del self.swap_space[key]

        print(f"[ENCERRAMENTO DE PROCESSO VIRTUAL] Processo '{process.name}' (PID {process.pid}) finalizado.")
        print(f"Molduras liberadas na RAM Dinâmica: {freed_frames if freed_frames else 'Nenhuma'} | Páginas removidas do Swap: {len(removed_swap)}.")

    def translate_address(self, process, page_num):
        """Converte Página Lógica -> Moldura Física consultando a Tabela de Páginas"""
        if page_num not in process.page_table:
            print(f"[SEGMENTATION FAULT]: Página Lógica {page_num} inválida para '{process.name}' (máx: {len(process.page_table) - 1}).")
            return None

        entry = process.page_table[page_num]
        print("[TRADUÇÃO DE ENDEREÇO: PÁGINA LÓGICA -> MOLDURA FÍSICA]")

        if entry["present"]:
            frame_id = entry["frame"]
            self.page_hits += 1
            self.frames[frame_id]["last_access"] = time.perf_counter()
            self.frames[frame_id]["ref_bit"] = 1
            print(f"Solicitação: Página Lógica {page_num} -> Mapeada na Moldura Física {frame_id} (RAM Dinâmica) [HIT]")
            return frame_id
        else:
            origin = "Swap (Disco)" if entry["in_swap"] else "Alocação por Demanda (não carregada)"
            print(f"Solicitação: Página Lógica {page_num} -> Ausente na RAM ({origin}) [MISS / PAGE FAULT]")
            print(f"Dica: Use a opção 6 (Executar passo da CPU) para carregar a Página {page_num} na RAM.")
            return None

    def _select_victim_frame(self):
        """Executa o algoritmo de substituição configurado (LRU, SECOND_CHANCE ou FIFO)"""
        if self.policy == "LRU":
            victim_idx = min(range(self.num_frames), key=lambda i: self.frames[i]["last_access"])
            victim = self.frames[victim_idx]
            elapsed_ms = max(1, int((time.perf_counter() - victim["last_access"]) * 1000))
            print(f"Memória RAM cheia. Executando Substituição de Página (Algoritmo LRU):")
            print(f"- Analisando histórico de acesso: Página Lógica {victim['page_num']} do PID {victim['pid']} não é usada há {elapsed_ms}ms (Mais antiga).")
            return victim_idx

        elif self.policy == "SECOND_CHANCE":
            print(f"Memória RAM cheia. Executando Substituição de Página (Algoritmo SEGUNDA CHANCE):")
            while True:
                candidate = self.frames[self.clock_hand]
                if candidate["ref_bit"] == 1:
                    print(
                        f"- [Segunda Chance] Moldura {self.clock_hand} "
                        f"(PID {candidate['pid']}, Página {candidate['page_num']}): "
                        f"Bit R=1 -> Segunda chance concedida (Bit R zerado para 0)."
                    )
                    candidate["ref_bit"] = 0
                    self.clock_hand = (self.clock_hand + 1) % self.num_frames
                else:
                    victim_idx = self.clock_hand
                    print(
                        f"- [Vítima Selecionada] Moldura {victim_idx} "
                        f"(PID {candidate['pid']}, Página {candidate['page_num']}): Bit R=0 -> Escolhida para remoção."
                    )
                    self.clock_hand = (self.clock_hand + 1) % self.num_frames
                    return victim_idx

        else:  # FIFO
            victim_idx = min(range(self.num_frames), key=lambda i: self.frames[i]["loaded_at"])
            victim = self.frames[victim_idx]
            print(f"Memória RAM cheia. Executando Substituição de Página (Algoritmo FIFO):")
            print(f"- Analisando fila de chegada: Página Lógica {victim['page_num']} do PID {victim['pid']} foi a primeira a entrar na RAM.")
            return victim_idx

    def access_page(self, process, page_num, instruction=""):
        """Simula execução de instrução na CPU que referencia uma Página Lógica"""
        if page_num not in process.page_table:
            print(f"[SEGMENTATION FAULT]: Instrução '{instruction}' tentou acessar Página Lógica {page_num} fora dos limites de '{process.name}'.")
            return

        print("[CPU - REFERÊNCIA DE MEMÓRIA EM EXECUÇÃO]")
        print(f"{process.name} requisita acesso à Página Lógica {page_num}...")

        entry = process.page_table[page_num]
        if entry["present"]:
            frame_id = entry["frame"]
            self.page_hits += 1
            self.frames[frame_id]["last_access"] = time.perf_counter()
            self.frames[frame_id]["ref_bit"] = 1
            print(f"- Consulta Tabela de Páginas -> Página Lógica {page_num} PRESENTE na Moldura Física {frame_id} (RAM Dinâmica) [HIT].")
            return

        # PAGE FAULT
        self.page_faults += 1
        print(f"- Consulta Tabela de Páginas -> Página Lógica {page_num} NÃO ESTÁ NA RAM!")
        print(f"\n[PAGE FAULT DETECTADO]: Página Lógica {page_num} ausente na RAM!")

        free_frame = next((i for i, f in enumerate(self.frames) if f is None), None)
        from_swap = entry["in_swap"]

        if free_frame is not None:
            target_frame = free_frame
            origem = "Swap (Disco)" if from_swap else "Memória Secundária (Demanda)"
            print(f"Moldura livre encontrada na RAM Dinâmica (Moldura Física {target_frame}).")
            print(f"- Carregando Página Lógica {page_num} do {process.name} da {origem} na Moldura Física {target_frame}.")
        else:
            target_frame = self._select_victim_frame()
            victim = self.frames[target_frame]
            victim_proc = victim["process"]
            victim_page = victim["page_num"]

            print(f"- Removendo Página Lógica {victim_page} do PID {victim_proc.pid} da RAM -> Salvando no Swap (Disco).")
            victim_proc.page_table[victim_page]["present"] = False
            victim_proc.page_table[victim_page]["frame"] = None
            victim_proc.page_table[victim_page]["in_swap"] = True
            self.swap_space[(victim_proc.pid, victim_page)] = {
                "process_name": victim_proc.name,
                "saved_at": time.perf_counter()
            }
            self.swap_outs += 1

            print(f"- Carregando Página Lógica {page_num} do {process.name} na Moldura Física {target_frame} (RAM Dinâmica).")

        if from_swap and (process.pid, page_num) in self.swap_space:
            del self.swap_space[(process.pid, page_num)]

        now = time.perf_counter()
        self.frames[target_frame] = {
            "pid": process.pid,
            "process": process,
            "page_num": page_num,
            "loaded_at": now,
            "last_access": now,
            "ref_bit": 1
        }
        entry["present"] = True
        entry["frame"] = target_frame
        entry["in_swap"] = False

        print(f"- Tabela de Páginas atualizada: Página Lógica {page_num} ---> Moldura Física {target_frame}.")

    def get_metrics(self, normal_processes):
        used_frames = sum(1 for f in self.frames if f is not None)
        total_kb = (self.num_frames * self.page_size) // 1024
        used_kb = (used_frames * self.page_size) // 1024
        total_internal_frag = sum(p.internal_fragmentation_bytes for p in normal_processes)
        return {
            "total_frames": self.num_frames,
            "used_frames": used_frames,
            "free_frames": self.num_frames - used_frames,
            "total_kb": total_kb,
            "used_kb": used_kb,
            "swap_pages": len(self.swap_space),
            "page_faults": self.page_faults,
            "page_hits": self.page_hits,
            "swap_outs": self.swap_outs,
            "internal_frag_bytes": total_internal_frag
        }

    def print_status(self, normal_processes):
        m = self.get_metrics(normal_processes)
        pct = (m["used_frames"] / m["total_frames"]) * 100 if m["total_frames"] else 0

        print(f"--- MAPA DA ÁREA DINÂMICA / MEMÓRIA VIRTUAL (Total: {m['total_frames']} Molduras x {self.page_size // 1024} KB = {m['total_kb']} KB) ---")
        print(f"Política de Substituição Ativa : {self.policy}")
        print(f"Ocupação da RAM Dinâmica       : {m['used_frames']}/{m['total_frames']} molduras ({m['used_kb']} KB / {m['total_kb']} KB - {pct:.1f}%)")
        print(f"Estatísticas de Acesso         : {m['page_hits']} HIT(s) | {m['page_faults']} PAGE FAULT(s) | {m['swap_outs']} SWAP-OUT(s)\n")

        print("Molduras Físicas (RAM Dinâmica):")
        now = time.perf_counter()
        for f_idx, frame in enumerate(self.frames):
            if frame is None:
                print(f"  [Moldura {f_idx:02d}] : [LIVRE]")
            else:
                age_ms = max(1, int((now - frame["last_access"]) * 1000))
                print(
                    f"  [Moldura {f_idx:02d}] : {frame['process'].name:<18} "
                    f"(PID {frame['pid']}) | Página Lógica {frame['page_num']} "
                    f"| Bit R={frame['ref_bit']} | Último uso: há {age_ms}ms"
                )

        print("\nÁrea de Swap (Memória Secundária):")
        if not self.swap_space:
            print("  (Vazia - nenhuma página enviada para Swap)")
        else:
            for (pid, p_num), info in self.swap_space.items():
                print(f"  - PID {pid} ({info['process_name']}): Página Lógica {p_num} [EM SWAP]")

        print("\n--- RELATÓRIO DE FRAGMENTAÇÃO INTERNA (PROCESSOS PAGINADOS) ---")
        if not normal_processes:
            print("  Nenhum processo paginado ativo.")
        else:
            for p in normal_processes:
                num_pages = len(p.page_table)
                in_ram = sum(1 for e in p.page_table.values() if e["present"])
                print(
                    f"  - {p.name:<18} (PID {p.pid}) | {num_pages} pág(s) "
                    f"({in_ram} na RAM) | Desperdício interno: {p.internal_fragmentation_bytes} Bytes"
                )
            print(f"Fragmentação Interna Total no Sistema: {m['internal_frag_bytes']} Bytes ({m['internal_frag_bytes'] / 1024:.2f} KB).")


class MemoryManager:
    """Controlador Híbrido de Memória (Área Reservada Contígua + Área Virtual Paginada)"""
    def __init__(self, reserved_kb=4096, dynamic_frames=4, page_size=4096):
        self.reserved = ReservedMemoryManager(total_kb=reserved_kb)
        self.virtual = VirtualMemoryManager(num_frames=dynamic_frames, page_size=page_size, policy="LRU")
        self.processes = {}  # {name: Process}
        self.next_pid = 101

        self._bootstrap_background_processes()

    def _bootstrap_background_processes(self):
        p1 = Process(self.next_pid, "Sys_Daemon", 4096, "normal", owner="root")
        self.next_pid += 1
        self.virtual.register_process(p1)
        self.virtual.preload_page(p1, 0, age_ms=15, ref_bit=1)
        self.processes[p1.name] = p1

        p2 = Process(self.next_pid, "Bg_Service", 8192, "normal", owner="root")
        self.next_pid += 1
        self.virtual.register_process(p2)
        self.virtual.preload_page(p2, 0, age_ms=45, ref_bit=0)
        self.virtual.preload_page(p2, 1, age_ms=25, ref_bit=1)
        self.processes[p2.name] = p2

    @staticmethod
    def parse_size_to_bytes(size_str):
        s = size_str.strip().upper()
        if s.endswith("MB"):
            return int(float(s[:-2]) * 1024 * 1024)
        elif s.endswith("KB"):
            return int(float(s[:-2]) * 1024)
        elif s.endswith("B"):
            return int(float(s[:-1]))
        else:
            return int(float(s) * 1024)

    def create_process(self, name, size_str, proc_type, owner="root"):
        """Aloca o processo e retorna a instância criada (sem exibir listas extras)"""
        if name in self.processes or name == "Núcleo Base do SO":
            print(f"Erro: Já existe um processo ativo com o nome '{name}'.")
            return None

        try:
            size_bytes = self.parse_size_to_bytes(size_str)
        except ValueError:
            print(f"Erro: Tamanho '{size_str}' inválido. Exemplos: 512KB, 10KB, 1MB.")
            return None

        if size_bytes <= 0:
            print("Erro: O tamanho do processo deve ser maior que zero.")
            return None

        ptype = proc_type.strip().lower()
        if ptype == "critical":
            size_kb = max(1, math.ceil(size_bytes / 1024))
            if self.reserved.allocate(name, size_kb):
                proc = Process(self.next_pid, name, size_bytes, "critical", owner=owner)
                self.next_pid += 1
                self.processes[name] = proc
                return proc
            return None
        elif ptype in ("normal", "medium"):
            proc = Process(self.next_pid, name, size_bytes, "normal", owner=owner)
            self.next_pid += 1
            self.virtual.register_process(proc)
            self.processes[name] = proc
            print(f"\n[ALOCAÇÃO CONCLUÍDA] Processo '{proc.name}' (PID {proc.pid}) devidamente alocado na Memória Virtual.")
            return proc
        else:
            print("Erro: Tipo inválido. Use 'critical' ou 'normal' (ou 'medium').")
            return None

    def terminate_process(self, name):
        if name == "Núcleo Base do SO":
            print("[NEGADO]: O 'Núcleo Base do SO' não pode ser finalizado.")
            return

        if name not in self.processes:
            print(f"Erro: Processo '{name}' não encontrado.")
            return

        proc = self.processes[name]
        if proc.proc_type == "critical":
            if self.reserved.deallocate(name):
                del self.processes[name]
        else:
            self.virtual.release_process(proc)
            del self.processes[name]

    def translate_address(self, process_name, page_num):
        if process_name not in self.processes:
            print(f"Erro: Processo '{process_name}' não encontrado.")
            return
        proc = self.processes[process_name]
        if proc.proc_type != "normal":
            print(f"Aviso: '{process_name}' é um processo crítico alocado de forma contígua na Área Reservada (sem paginação).")
            return
        self.virtual.translate_address(proc, page_num)

    def execute_step(self, process_name, instruction, explicit_page=None):
        if process_name not in self.processes:
            print(f"Erro: Processo '{process_name}' não encontrado.")
            return
        proc = self.processes[process_name]
        if proc.proc_type != "normal":
            print(f"[CPU]: Executando instrução '{instruction}' no processo crítico '{process_name}' (Acesso direto à Área Reservada).")
            return

        page_num = explicit_page
        if page_num is None:
            match = re.search(r'(?:p[áa]gina|page)\s*(\d+)', instruction, re.IGNORECASE)
            if not match:
                match = re.search(r'(\d+)', instruction)
            if not match:
                print(f"Erro: Não foi possível identificar o número da página na instrução '{instruction}'.")
                return
            page_num = int(match.group(1))

        self.virtual.access_page(proc, page_num, instruction)

    def memory_status(self, scope="all"):
        normal_procs = [p for p in self.processes.values() if p.proc_type == "normal"]

        if scope == "reserved":
            self.reserved.print_status()
        elif scope == "virtual":
            self.virtual.print_status(normal_procs)
        else:
            r = self.reserved.get_metrics()
            v = self.virtual.get_metrics(normal_procs)
            r_pct = (r["used_kb"] / r["total_kb"]) * 100
            v_pct = (v["used_frames"] / v["total_frames"]) * 100

            print("===================================================================")
            print("  ANÁLISE CONSOLIDADA DE OCUPAÇÃO DA MEMÓRIA (MODELO HÍBRIDO)")
            print("===================================================================")
            print(f"[1] RAM Crítica/Reservada (Contígua) : {r['used_kb']} KB / {r['total_kb']} KB ({r_pct:.1f}%) | Livre: {r['free_kb']} KB")
            print(f"    Fragmentação Externa             : {'SIM (' + str(r['free_fragments']) + ' lacunas)' if r['has_external_fragmentation'] else 'NÃO'}")
            print(f"[2] RAM Dinâmica/Virtual (Paginada)  : {v['used_kb']} KB / {v['total_kb']} KB ({v_pct:.1f}%) | Molduras: {v['used_frames']}/{v['total_frames']}")
            print(f"    Swap (Memória Secundária)        : {v['swap_pages']} página(s) | Política: {self.virtual.policy}")
            print(f"    Fragmentação Interna Total       : {v['internal_frag_bytes']} Bytes")
            print("===================================================================\n")
            self.reserved.print_status()
            print("")
            self.virtual.print_status(normal_procs)
            print("")
            self.list_processes()

    def memory_compact(self):
        self.reserved.compact()

    def list_processes(self):
        print("--- TABELA DE PROCESSOS ATIVOS ---")
        print(f"{'PID':<6} {'NOME':<22} {'TIPO':<12} {'TAMANHO':<12} {'DONO'}")
        print(f"{'0':<6} {'Núcleo Base do SO':<22} {'critical':<12} {'1024 KB':<12} root")
        for p in self.processes.values():
            kb = p.size_bytes / 1024
            kb_str = f"{int(kb)} KB" if kb.is_integer() else f"{kb:.1f} KB"
            print(f"{p.pid:<6} {p.name:<22} {p.proc_type:<12} {kb_str:<12} {p.owner}")

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
        
        self.owner = owner
        self.group = group
        self.permissions = perms
        self.is_encrypted = False
        self.integrity_hash = None
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
        self.memory = MemoryManager()
        
        self.root = Node("/", is_dir=True, owner="root", group="admin", perms="rwxr-xr-x")
        self.disk.allocate_blocks(1)
        
        self._create_system_file()

    def _create_system_file(self):
        sys_dir = Node("sistema", is_dir=True, parent=self.root, owner="root", group="admin", perms="rwxr-xr-x")
        self.root.children["sistema"] = sys_dir
        
        config = Node("config.sys", is_dir=False, parent=sys_dir, size_bytes=1024, owner="root", group="admin", perms="rwxr-x---")
        config.data_blocks = self.disk.allocate_blocks(2)[1:]
        
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

        perms = "rw-r-----" if self.security.current_user != "root" else "rwxr-xr-x"
        
        new_file = Node(missing, is_dir=False, parent=parent, size_bytes=size_bytes,
                        owner=self.security.current_user, group=self.security.current_group, perms=perms)
        new_file.inode_block = blocks[0]
        new_file.data_blocks = blocks[1:]
        
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
            self.disk.blocks[b_idx]["data_raw"] = cipher
            
        node.is_encrypted = True
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
            self.disk.blocks[node.data_blocks[0]]["data_raw"] = "###PAYLOAD_MALICIOSO###"
            print(f"[!] HACK SIMULADO: Bloco físico do arquivo '{path}' adulterado por fora do Sistema de Arquivos.")

# =====================================================================
# CLI - TECLA INSTANTÂNEA PARA NÚMEROS + COMANDO 'status' + SIM/NÃO
# =====================================================================
def ler_tecla_ou_comando(mensagem):
    """
    Se pressionar um número (0-9): retorna instantaneamente sem precisar de Enter.
    Se digitar um comando textual (ex: 'status'): lê até o Enter.
    """
    print(mensagem, end="", flush=True)

    if not sys.stdin.isatty():
        return input().strip().lower()

    if os.name == "nt":
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):  # Ignora teclas especiais
                msvcrt.getwch()
                continue
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in ("\r", "\n", " "):
                continue
            if ch.isdigit():
                print(ch)
                return ch
            print(ch, end="", flush=True)
            resto = input()
            return (ch + resto).strip().lower()
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        while True:
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in ("\r", "\n", " "):
                continue
            if ch.isdigit():
                print(ch)
                return ch
            print(ch, end="", flush=True)
            resto = input()
            return (ch + resto).strip().lower()

def ler_campo(mensagem):
    """Lê um dado textual (pressiona Enter ao concluir o campo)"""
    valor = input(mensagem).strip()
    if not valor:
        print("⚠️  Operação cancelada: campo obrigatório não informado.")
        return None
    return valor

def confirmar_sim_nao(mensagem):
    """Solicita confirmação explícita digitando sim ou não"""
    while True:
        resp = input(mensagem).strip().lower()
        if resp in ("sim", "s"):
            return True
        if resp in ("não", "nao", "n"):
            return False
        print("⚠️  Resposta inválida. Digite 'sim' ou 'não'.")

def exibir_submenu_status(fs):
    print("\nEscopo do Status: [1] Área Reservada \n[2] Memória Virtual \n[3] Análise Consolidada Completa")
    escopo_op = ler_tecla_ou_comando("Pressione 1, 2 ou 3: ")
    mapa_escopo = {"1": "reserved", "2": "virtual", "3": "all"}
    if escopo_op in mapa_escopo:
        fs.memory.memory_status(mapa_escopo[escopo_op])
    else:
        print("⚠️  Escopo inválido.")

def menu_seguranca(fs):
    while True:
        usuario = fs.security.current_user or "visitante"
        print("\n---------------------------------------------------------------------")
        print(f" 🔐 MÓDULO DE SEGURANÇA & USUÁRIOS  [Sessão: {usuario} | {fs.security.mode}]")
        print("---------------------------------------------------------------------")
        print("  1 - Login (Autenticar usuário)")
        print("  2 - Logout (Encerrar sessão)")
        print("  3 - Criar novo usuário (useradd - Apenas Root)")
        print("  4 - Alterar permissões (chmod)")
        print("  5 - Varredura de integridade / Antivírus (antivirus_scan)")
        print("  6 - Simular invasão no disco físico (hack_disk)")
        print("  0 - Voltar ao menu principal")

        op = ler_tecla_ou_comando("\nPressione o nº da opção: ")
        if op == "0":
            break
        elif op == "status":
            exibir_submenu_status(fs)
        elif op == "1":
            user = ler_campo("Usuário: ")
            if not user: continue
            pwd = ler_campo(f"Senha para {user}: ")
            if not pwd: continue
            if fs.security.login(user, pwd):
                print(f"\nAutenticado com sucesso. Usuário: '{user}' | Grupo: '{fs.security.current_group}' | Modo: {fs.security.mode}")
            else:
                print("Falha na autenticação.")
        elif op == "2":
            fs.security.logout()
            print("Sessão encerrada.")
        elif op == "3":
            if fs.security.mode != "MODO_KERNEL":
                print("[NEGADO]: Operação restrita. Apenas usuários com permissão de Admin ou root podem criar usuários.")
                continue
            nome = ler_campo("Nome do novo usuário: ")
            if not nome: continue
            grupo = ler_campo("Grupo do usuário: ")
            if not grupo: continue
            senha = ler_campo("Senha: ")
            if not senha: continue
            fs.security._register_user(nome, grupo, senha)
            print(f"Usuário '{nome}' (Grupo: {grupo}) criado com sucesso no banco de dados.")
        elif op == "4":
            caminho = ler_campo("Caminho do arquivo/diretório (ex: /docs/texto.txt): ")
            if not caminho: continue
            perm = ler_campo("Permissões (9 caracteres, ex: rwxr-xr-x): ")
            if not perm: continue
            fs.chmod(caminho, perm)
        elif op == "5":
            fs.antivirus_scan()
        elif op == "6":
            caminho = ler_campo("Caminho do arquivo para adulterar no disco físico: ")
            if not caminho: continue
            fs.corrupt_file_for_test(caminho)
        else:
            print("⚠️  Opção inválida.")

def menu_arquivos(fs):
    while True:
        usuario = fs.security.current_user or "visitante"
        print("\n---------------------------------------------------------------------")
        print(f" 📁 MÓDULO DE SISTEMA DE ARQUIVOS   [Sessão: {usuario} | {fs.security.mode}]")
        print("---------------------------------------------------------------------")
        print("  1 - Criar diretório (mkdir)")
        print("  2 - Criar arquivo (create_file)")
        print("  3 - Ler arquivo (read_file)")
        print("  4 - Criptografar arquivo (encrypt_file)")
        print("  0 - Voltar ao menu principal")

        op = ler_tecla_ou_comando("\nPressione o nº da opção: ")
        if op == "0":
            break
        elif op == "status":
            exibir_submenu_status(fs)
        elif op == "1":
            caminho = ler_campo("Caminho do novo diretório (ex: /docs): ")
            if not caminho: continue
            fs.mkdir(caminho)
        elif op == "2":
            caminho = ler_campo("Caminho do novo arquivo (ex: /docs/texto.txt): ")
            if not caminho: continue
            conteudo = ler_campo("Conteúdo do arquivo: ")
            if not conteudo: continue
            fs.create_file(caminho, conteudo)
        elif op == "3":
            caminho = ler_campo("Caminho do arquivo para leitura: ")
            if not caminho: continue
            fs.read_file(caminho)
        elif op == "4":
            caminho = ler_campo("Caminho do arquivo para criptografar: ")
            if not caminho: continue
            chave = ler_campo("Chave de criptografia: ")
            if not chave: continue
            fs.encrypt_file(caminho, chave)
        else:
            print("⚠️  Opção inválida.")

def menu_memoria(fs):
    while True:
        print("\n---------------------------------------------------------------------")
        print(f" 🧠 GERENCIAMENTO DE MEMÓRIA HÍBRIDA [Política: {fs.memory.virtual.policy}]")
        print("---------------------------------------------------------------------")
        print("  1 - Criar processo (create_process)")
        print("  2 - Encerrar processo (terminate_process)")
        print("  3 - Status da memória e fragmentação (ou digite 'status')")
        print("  4 - Compactar Área Reservada da RAM (memory_compact)")
        print("  5 - Traduzir endereço lógico -> moldura (translate_address)")
        print("  6 - Executar passo da CPU / Page Fault (execute_step)")
        print("  7 - Alterar algoritmo de substituição (set_policy)")
        print("  8 - Listar processos ativos (ps)")
        print("  0 - Voltar ao menu principal")

        op = ler_tecla_ou_comando("\nPressione o nº da opção (ou digite 'status'): ")
        if op == "0":
            break
        elif op == "1":
            nome = ler_campo("Nome do processo (ex: Kernel_DiskDriver ou App_Navegador): ")
            if not nome: continue
            tamanho = ler_campo("Tamanho do processo (ex: 512KB, 10KB, 1MB): ")
            if not tamanho: continue
            print("Tipo do processo: [1] critical (Área Reservada) | [2] normal/medium (Memória Virtual)")
            tipo_op = ler_tecla_ou_comando("Pressione 1 ou 2: ")
            mapa_tipo = {"1": "critical", "2": "normal"}
            if tipo_op not in mapa_tipo:
                print("⚠️  Tipo inválido.")
                continue
            owner = fs.security.current_user or "root"
            proc = fs.memory.create_process(nome, tamanho, mapa_tipo[tipo_op], owner=owner)

            if proc and proc.proc_type == "normal":
                viu_algo = False
                if confirmar_sim_nao("Deseja visualizar o cálculo de páginas? (sim/não): "):
                    fs.memory.virtual.print_page_calculation(proc)
                    viu_algo = True
                if confirmar_sim_nao("Deseja visualizar a análise de fragmentação interna? (sim/não): "):
                    fs.memory.virtual.print_internal_fragmentation(proc)
                    viu_algo = True
                if not viu_algo:
                    print("Detalhes omitidos. Use o comando 'status' (ou opção 3) sempre que quiser consultá-los.")
            elif proc and proc.proc_type == "critical":
                print("Para ver o mapa completo e a fragmentação externa, use o comando 'status' (ou opção 3).")

        elif op == "2":
            nome = ler_campo("Nome do processo a encerrar: ")
            if not nome: continue
            fs.memory.terminate_process(nome)
        elif op in ("3", "status"):
            exibir_submenu_status(fs)
        elif op == "4":
            fs.memory.memory_compact()
        elif op == "5":
            proc = ler_campo("Nome do processo: ")
            if not proc: continue
            pag_str = ler_campo("Número da Página Lógica (ex: 0, 1, 2): ")
            if not pag_str: continue
            if not pag_str.isdigit():
                print("Erro: Informe um número inteiro válido para a página.")
                continue
            fs.memory.translate_address(proc, int(pag_str))
        elif op == "6":
            proc = ler_campo("Nome do processo: ")
            if not proc: continue
            instrucao = ler_campo("Instrução (ex: LOAD_DATA Página 2) ou nº da página: ")
            if not instrucao: continue
            fs.memory.execute_step(proc, instrucao)
        elif op == "7":
            print("Política: [1] LRU | [2] SECOND_CHANCE (Segunda Chance) | [3] FIFO")
            pol_op = ler_tecla_ou_comando("Pressione 1, 2 ou 3: ")
            mapa_pol = {"1": "LRU", "2": "SECOND_CHANCE", "3": "FIFO"}
            if pol_op in mapa_pol:
                fs.memory.virtual.set_policy(mapa_pol[pol_op])
            else:
                print("⚠️  Opção inválida.")
        elif op == "8":
            fs.memory.list_processes()
        else:
            print("⚠️  Opção inválida.")

if __name__ == "__main__":
    fs = FileSystem()
    print("🔐 Simulador de Sistema Operacional 🔐")
    print("Usuários padrão disponíveis para teste:")
    print("  • root   (senha: root123)")
    print("  • carlos (senha: senha123)")

    try:
        while True:
            usuario = fs.security.current_user or "visitante"
            print("\n=====================================================================")
            print(f" 💻 MENU PRINCIPAL DO SO            [Sessão: {usuario} | {fs.security.mode}]")
            print("=====================================================================")
            print("  1 - Segurança e Usuários (Login, ACL, Antivírus)")
            print("  2 - Sistema de Arquivos (Diretórios, Arquivos, Criptografia)")
            print("  3 - Gerenciamento de Memória Híbrida (RAM Reservada & Virtual)")
            print("  0 - Sair do simulador")
            print("  * Dica: digite 'status' + Enter a qualquer momento para ver a memória")
            print("=====================================================================")

            op = ler_tecla_ou_comando("Pressione o nº da opção (ou digite 'status'): ")
            if op == "0":
                print("Encerrando o simulador...")
                break
            elif op == "status":
                exibir_submenu_status(fs)
            elif op == "1":
                menu_seguranca(fs)
            elif op == "2":
                menu_arquivos(fs)
            elif op == "3":
                menu_memoria(fs)
            else:
                print("⚠️  Opção inválida.")
    except KeyboardInterrupt:
        print("\nSimulador encerrado pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {e}")