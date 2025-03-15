# app paketi başlatma dosyası
from flask import Flask, render_template, request, jsonify, session
import os
import json
import logging
import traceback
from app.utils.transcript_processor import TranscriptProcessor
from app.utils.ai_analyzer import AIAnalyzer
from app.utils.test_generator import TestGenerator
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Loglama yapılandırması
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Flask uygulamasını oluştur
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

@app.route('/')
def index():
    """Ana sayfa."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_transcript():
    """Transkript dosyasını yükle ve işle."""
    try:
        if 'transcript_file' not in request.files:
            return jsonify({'success': False, 'error': 'Dosya bulunamadı.'}), 400
        
        file = request.files['transcript_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400
        
        # Dosyayı geçici olarak kaydet
        temp_file_path = os.path.join('temp', file.filename)
        os.makedirs('temp', exist_ok=True)
        file.save(temp_file_path)
        
        # Transkripti işle
        processor = TranscriptProcessor(temp_file_path)
        if not processor.load_transcript():
            return jsonify({'success': False, 'error': 'Transkript yüklenemedi.'}), 400
        
        processed_data = processor.process_transcript()
        
        # Yapay zeka analizi
        analyzer = AIAnalyzer()
        analysis_result = analyzer.analyze_transcript(processed_data)
        
        if not analysis_result.get('success', False):
            return jsonify({'success': False, 'error': 'Analiz başarısız oldu.'}), 500
        
        # Test oluştur
        logger.debug("Testler oluşturuluyor...")
        tests_result = analyzer.generate_tests(analysis_result, processed_data)
        logger.debug(f"Test sonucu: {tests_result}")
        
        if not tests_result.get('success', False):
            return jsonify({'success': False, 'error': 'Test oluşturma başarısız oldu.'}), 500
        
        # Sonuçları oturumda sakla
        session['analysis_result'] = analysis_result
        session['tests_result'] = tests_result
        
        # Özet bilgileri döndür
        return jsonify({
            'success': True,
            'message': 'Transkript başarıyla analiz edildi ve testler oluşturuldu.',
            'redirect': '/results'
        })
    except Exception as e:
        # Hata detaylarını logla
        logger.error(f"Upload işlemi sırasında hata: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Hata mesajını JSON olarak döndür
        return jsonify({
            'success': False,
            'error': f'İşlem sırasında bir hata oluştu: {str(e)}'
        }), 500

@app.route('/results')
def results():
    """Analiz sonuçlarını ve testleri göster."""
    try:
        # Oturumdan sonuçları al
        analysis_result = session.get('analysis_result', {})
        tests_result = session.get('tests_result', {})
        
        logger.debug(f"Analiz sonucu: {analysis_result}")
        logger.debug(f"Test sonucu: {tests_result}")
        
        if not analysis_result or not tests_result:
            return render_template('error.html', error='Sonuçlar bulunamadı. Lütfen transkript yükleyin.')
        
        # Test verilerini işle
        test_generator = TestGenerator(tests_result.get('raw_tests', ''))
        processed_tests = test_generator.process_tests()
        logger.debug(f"İşlenmiş testler: {processed_tests}")
        tests_html = test_generator.get_tests_as_html()
        
        return render_template(
            'results.html',
            analysis=analysis_result.get('raw_analysis', ''),
            tests_html=tests_html
        )
    except Exception as e:
        # Hata detaylarını logla
        logger.error(f"Results sayfası gösterilirken hata: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Hata sayfasını göster
        return render_template('error.html', error=f'Sonuçlar gösterilirken bir hata oluştu: {str(e)}') 