from typing import NamedTuple
import re


class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.prev_dtg = b''
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)

    def tratar_datagrama_saida(self, datagrama: str):
        dtg = datagrama.replace(b'\xdb', b'\xdb\xdd')
        dtg = dtg.replace(b'\xc0', b'\xdb\xdc')
        dtg = b'\xc0' + dtg + b'\xc0'
        return dtg

    def tratar_datagrama_entrada(self, datagrama: str):
        dtg = datagrama.replace(b'\xdb\xdc', b'\xc0')
        dtg = dtg.replace(b'\xdb\xdd', b'\xdb')
        dtg = dtg.strip(b'\xc0')
        return dtg

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # TODO: Preencha aqui com o código para enviar o datagrama pela linha
        # serial, fazendo corretamente a delimitação de quadros e o escape de
        # sequências especiais, de acordo com o protocolo CamadaEnlace (RFC 1055).
        dtg = self.tratar_datagrama_saida(datagrama)
        self.linha_serial.enviar(dtg)

    def separar_pacotes(self, dados: str):
        END_count = dados.count(b'\xc0')
        dados_sep = dados.split(b'\xc0')

        if dados.startswith(b'\xc0') and self.prev_dtg != b'':
            print('caso1')
            self.callback(self.prev_dtg)
            self.prev_dtg = b''

        if dados_sep[-1] != b'':
            self.prev_dtg += dados_sep[-1]
            print("buffer: ", self.prev_dtg)
            dados_sep = dados_sep[:-1]
        dados_sep = list(filter(lambda x: x != b'', dados_sep))
        print("depois filter: ", dados_sep)

        if not dados.startswith(b'\xc0') and END_count > 0 and self.prev_dtg != b'':
            print('caso2')
            self.callback(self.prev_dtg + dados_sep[0])
            self.prev_dtg = b''
            dados_sep.pop(0)

        if len(dados_sep) == 0 and self.prev_dtg != b'' and not dados.startswith(b'\xc0') and END_count > 0:
            print('caso3')
            self.callback(self.prev_dtg)
            self.prev_dtg = b''
            return

        for d in dados_sep:
            self.callback(d)
        print(dados_sep)
        pass

    def __raw_recv(self, dados: str):
        # TODO: Preencha aqui com o código para receber dados da linha serial.
        # Trate corretamente as sequências de escape. Quando ler um quadro
        # completo, repasse o datagrama contido nesse quadro para a camada
        # superior chamando self.callback. Cuidado pois o argumento dados pode
        # vir quebrado de várias formas diferentes - por exemplo, podem vir
        # apenas pedaços de um quadro, ou um pedaço de quadro seguido de um
        # pedaço de outro, ou vários quadros de uma vez só.
        print("recebido: ", dados)

        dados_sep = self.separar_pacotes(dados)
