FROM tryton/tryton:7.6

# Install additional Python dependencies here if needed
# RUN pip install --no-cache-dir some-package

# Copy custom modules into the image
COPY ./tryton/modules /opt/trytond/modules

# Copy default configuration
COPY ./config/trytond.conf /etc/tryton/trytond.conf

# Expose Tryton port
EXPOSE 8000

CMD ["trytond", "-c", "/etc/tryton/trytond.conf"]
