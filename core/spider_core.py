#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

import gevent
import gevent.monkey
import logging

from downloader.requests_downloader import RequestsDownLoader
from downloader.spider_request import Request
from scheduler.url_scheduler import UrlScheduler


gevent.monkey.patch_all()
reload(sys)
sys.setdefaultencoding('utf-8')
logger = logging.getLogger('core')


class SpiderCore(object):
    def __init__(self, processor, downloader=None, scheduler=None):
        self._processor = processor
        self._spider_status = 0
        self._pipelines = []
        self._spider_name = processor.spider_name
        self._spider_id = processor.spider_id
        self._start_request = None

        if not downloader:
            self._downloader = RequestsDownLoader()

        if not scheduler:
            self._scheduler = UrlScheduler(self._spider_id)

    def create(self, processor):
        self._processor = processor
        return self

    def set_scheduler(self, scheduler):
        self._scheduler = scheduler
        return self

    def set_downloader(self, downloader):
        self._downloader = downloader
        return self

    def set_pipeline(self, pipeline):
        self._pipelines.append(pipeline)
        return self

    def get_status(self):
        return self._spider_status

    def init_component(self):
        pass

    def set_start_request(self, request):
        self._start_request = request
        return self

    def start(self):
        if self._start_request:
            self._start_request.callback = self._processor.process
            self._scheduler.push(self._start_request, False)
        for batch in self._batch_requests():
            if len(batch) > 0:
                logger.info('batch:', len(batch))
                gevent.joinall([gevent.spawn(self._crawl, r) for r in batch])
                logger.info('batch end')

    def _batch_requests(self):
        batch = []
        count = 0
        while True:
            count += 1
            if len(batch) > 99 or count > 99:
                yield batch
                batch = []
                count = 0
            temp_request = self._scheduler.poll()
            if temp_request:
                batch.append(temp_request)

    def _crawl(self, request):
        response = self._downloader.download(request)
        for item in request.callback(response):
            if isinstance(item, Request):
                self._scheduler.push(item)
            else:
                for pipeline in self._pipelines:
                    pipeline.process_item(item)
