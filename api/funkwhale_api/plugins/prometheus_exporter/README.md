Prometheus exporter for Funkwhale
=================================

Use the following prometheus config:

.. code-block: yaml

  global:
    scrape_interval: 15s

  scrape_configs:
    - job_name: funkwhale
      static_configs:
        - targets: ['yourpod']
      metrics_path: /api/plugins/prometheus/metrics?token=test

    - job_name: prometheus
      static_configs:
        - targets: ['localhost:9090']
