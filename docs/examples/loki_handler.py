"""Custom logging handler для отправки логов в Loki.

Важно: не используем стандартный логгер внутри обработчиков, чтобы избежать
рекурсии/взаимной блокировки при ошибках отправки (handler -> logger -> handler ...).
Все внутренние ошибки пишем напрямую в stderr.
"""
import logging
import os
import json
import time
from datetime import datetime
from typing import Dict, Any
import requests
from threading import Lock, Thread
import queue
import sys



LOKI_URL = os.getenv('LOKI_URL', 'http://loki:3100')


class LokiHandler(logging.Handler):
    """Handler для отправки логов в Loki через HTTP API."""
    
    def __init__(self, url: str = None, labels: Dict[str, str] = None):
        """
        Инициализация handler.
        
        Args:
            url: URL Loki сервера
            labels: Метки для логов
        """
        super().__init__()
        self.url = (url or LOKI_URL).rstrip('/') + '/loki/api/v1/push'
        self.labels = labels or {}
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.lock = Lock()
        
        # Базовые метки
        if 'service' not in self.labels:
            self.labels['service'] = 'telegram-fetcher'
        if 'environment' not in self.labels:
            self.labels['environment'] = os.getenv('ENVIRONMENT', 'development')
    
    def emit(self, record: logging.LogRecord):
        """Отправить лог в Loki."""
        try:
            # Формируем запись лога
            log_entry = self.format_log_entry(record)
            
            # Отправляем в Loki
            with self.lock:
                self.send_to_loki(log_entry)
        except Exception as e:
            # Не падаем если не можем отправить лог
            try:
                sys.stderr.write(f"[loki_handler] Failed to send log to Loki: {e}\n")
            except Exception:
                pass
    
    def format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Форматировать запись лога для Loki."""
        # Создаем копию меток и добавляем level
        labels = self.labels.copy()
        labels['level'] = record.levelname.lower()
        labels['logger'] = record.name
        
        # Если есть extra поля, добавляем их как метки
        if hasattr(record, 'channel'):
            labels['channel'] = str(record.channel)
        
        # Формируем сообщение
        message = self.format(record)
        
        # Timestamp в наносекундах
        timestamp_ns = str(int(record.created * 1e9))
        
        return {
            'labels': labels,
            'timestamp': timestamp_ns,
            'line': message
        }
    
    def send_to_loki(self, log_entry: Dict[str, Any]):
        """Отправить лог в Loki."""
        # Формируем метки в формате {key1="value1",key2="value2"}
        labels_str = ','.join([f'{k}="{v}"' for k, v in log_entry['labels'].items()])
        labels_str = '{' + labels_str + '}'
        
        # Формируем payload для Loki
        payload = {
            'streams': [
                {
                    'stream': log_entry['labels'],
                    'values': [
                        [log_entry['timestamp'], log_entry['line']]
                    ]
                }
            ]
        }
        
        try:
            response = self.session.post(
                self.url,
                data=json.dumps(payload),
                timeout=5
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Логируем ошибку, но не падаем
            pass


class BatchLokiHandler(LokiHandler):
    """Handler с батчингом для эффективной отправки логов."""
    
    def __init__(self, url: str = None, labels: Dict[str, str] = None, 
                 batch_size: int = 10, flush_interval: float = 5.0):
        """
        Инициализация handler с батчингом.
        
        Args:
            url: URL Loki сервера
            labels: Метки для логов
            batch_size: Размер батча для отправки
            flush_interval: Интервал принудительной отправки (секунды)
        """
        super().__init__(url, labels)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch = []
        self.last_flush = time.time()
        self._stop = False
        self.queue = queue.Queue()
        # Фоновый поток для периодической отправки, чтобы не делать I/O внутри emit
        self._flusher = Thread(target=self._run_flusher, daemon=True)
        self._flusher.start()
    
    def emit(self, record: logging.LogRecord):
        """Добавить лог в батч (без сетевых вызовов)."""
        try:
            log_entry = self.format_log_entry(record)
            # Кладем в потокобезопасную очередь, чтобы не блокироваться в emit
            try:
                self.queue.put_nowait(log_entry)
            except queue.Full:
                try:
                    sys.stderr.write("[loki_handler] queue full, dropping log entry\n")
                except Exception:
                    pass
        except Exception as e:
            try:
                sys.stderr.write(f"[loki_handler] Failed to add log to batch: {e}\n")
            except Exception:
                pass

    def _run_flusher(self):
        """Фоновый цикл для периодической отправки батча."""
        while not self._stop:
            time.sleep(self.flush_interval)
            try:
                self.flush()
            except Exception:
                # Ошибки уже пишутся в stderr внутри flush
                pass
    
    def flush(self):
        """Отправить все логи из батча."""
        drained = []
        # Переливаем все накопленные элементы очереди
        try:
            while True:
                drained.append(self.queue.get_nowait())
        except queue.Empty:
            pass
        # Добавляем то, что могло быть во временном списке
        if self.batch:
            drained.extend(self.batch)
            self.batch.clear()
        if not drained:
            return
        
        try:
            # Группируем логи по меткам
            streams = {}
            for entry in drained:
                labels_key = json.dumps(entry['labels'], sort_keys=True)
                if labels_key not in streams:
                    streams[labels_key] = {
                        'stream': entry['labels'],
                        'values': []
                    }
                streams[labels_key]['values'].append([
                    entry['timestamp'],
                    entry['line']
                ])
            
            # Формируем payload
            payload = {
                'streams': list(streams.values())
            }
            
            # Отправляем
            response = self.session.post(
                self.url,
                data=json.dumps(payload),
                timeout=5
            )
            response.raise_for_status()
            
            # Отмечаем время последней успешной отправки
            self.last_flush = time.time()
            
        except Exception as e:
            try:
                sys.stderr.write(f"[loki_handler] Failed to flush logs to Loki: {e}\n")
            except Exception:
                pass
            # Очищаем батч даже при ошибке, чтобы не росла память
            self.batch.clear()
            self.last_flush = time.time()
    
    def close(self):
        """Закрыть handler и отправить оставшиеся логи."""
        self._stop = True
        try:
            if hasattr(self, '_flusher') and self._flusher.is_alive():
                self._flusher.join(timeout=self.flush_interval + 0.5)
        except Exception:
            pass
        with self.lock:
            self.flush()
        super().close()


def get_loki_handler(batch: bool = True) -> logging.Handler:
    """
    Получить handler для Loki.
    
    Args:
        batch: Использовать батчинг
        
    Returns:
        Loki handler
    """
    if batch:
        return BatchLokiHandler()
    else:
        return LokiHandler()
