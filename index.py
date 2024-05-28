from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
import os
import logging
from logging.handlers import RotatingFileHandler
from subprocess import run
from werkzeug.utils import secure_filename

app = Flask(__name__)

PASTA_ARMAZENA_ARQUIVO = './arquivos'
PASTA_LOGS = './logs'
EXTENSOES_PERMITIDAS = {'pdf'}
TOKEN_SERVICO = 'dG9rZW5mYXdmd2FmYXdmd2Fmd2E='
RESOLUCOES_DISPONIVEIS = {
    72: '/screen',
    150: '/ebook',
    300: '/printer'
}

if not os.path.exists(PASTA_LOGS):
    os.makedirs(PASTA_LOGS)
log_handler = RotatingFileHandler(os.path.join(
    PASTA_LOGS, 'app.log'), maxBytes=10000, backupCount=1)
log_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)


def arquivo_permitido(nome_arquivo):
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS


def alterar_resolucao_pdf(caminho_pdf, resolucao):
    try:
        resolucao_ghostscript = RESOLUCOES_DISPONIVEIS.get(resolucao)
        caminho_saida = caminho_pdf.replace(
            '.pdf', f'_resolucao_{resolucao}.pdf')
        run(['gs', '-sDEVICE=pdfwrite', f'-dPDFSETTINGS={resolucao_ghostscript}', '-dNOPAUSE', '-dBATCH', '-dQUIET',
             f'-sOutputFile={caminho_saida}', caminho_pdf], check=True)
        return caminho_saida
    except Exception as e:
        return f"Erro: {str(e)}"


def registra_log(mensagem):
    app.logger.info(mensagem)


@app.route('/alterar-resolucao-pdf', methods=['POST'])
def rota_alterar_resolucao_pdf():
    if 'file' not in request.files:
        registra_log('Nenhum arquivo foi enviado')
        return jsonify({'erro': 'Nenhum arquivo foi enviado'}), 400

    arquivo = request.files['file']
    resolucao = request.form.get('resolucao', type=int)
    if arquivo.filename == '':
        registra_log('Nenhum arquivo foi selecionado')
        return jsonify({'erro': 'Nenhum arquivo foi selecionado'}), 400

    if not resolucao or resolucao not in RESOLUCOES_DISPONIVEIS:
        registra_log('Resolução não fornecida ou inválida')
        return jsonify({'erro': 'Resolução não fornecida ou inválida'}), 400

    if arquivo and arquivo_permitido(arquivo.filename):
        nome_arquivo = secure_filename(arquivo.filename)
        caminho_pdf = os.path.join(PASTA_ARMAZENA_ARQUIVO, nome_arquivo)
        os.makedirs(PASTA_ARMAZENA_ARQUIVO, exist_ok=True)
        arquivo.save(caminho_pdf)

        caminho_saida = alterar_resolucao_pdf(caminho_pdf, resolucao)
        if caminho_saida.startswith("Erro"):
            registra_log(f'Erro na redução de resolução do arquivo {
                         nome_arquivo}: {caminho_saida}')
            return jsonify({'erro': caminho_saida}), 500

        nome_saida = os.path.basename(caminho_saida)
        registra_log(f'Redução de resolução concluída para o arquivo {
                     nome_arquivo}, salvo como {nome_saida}')
        return redirect(url_for('download_arquivo', filename=nome_saida))
    else:
        registra_log(f'Arquivo não permitido: {arquivo.filename}')
        return jsonify({'erro': 'Arquivo não permitido'}), 400


@app.route('/download/<filename>', methods=['GET'])
def download_arquivo(filename):
    return send_from_directory(PASTA_ARMAZENA_ARQUIVO, filename, as_attachment=True)


def decode_text(input_text):
    try:
        return input_text.decode('utf-8')
    except UnicodeDecodeError as e:
        app.logger.error(f"Erro ao decodificar: {e}")
        return input_text.decode('utf-8', errors='ignore')


@app.route('/gera-relatorio', methods=['POST'])
def gera_relatorio():
    token = request.headers.get('Authorization')
    if token != TOKEN_SERVICO:
        registra_log('Acesso não autorizado ao serviço de log')
        return jsonify({'erro': 'Acesso não autorizado'}), 403
    try:
        with open(os.path.join(PASTA_LOGS, 'app.log'), 'rb') as log_file:
            log_content = log_file.read()
        decoded_log_content = decode_text(log_content)
        return jsonify({'relatorio': decoded_log_content}), 200
    except Exception as e:
        app.logger.error(f'Erro ao emitir relatório: {str(e)}')
        return jsonify({'erro': 'Erro ao emitir relatório'}), 500


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
