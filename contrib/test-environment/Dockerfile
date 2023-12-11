FROM idmslinux/rolling

RUN set -ex; \
    echo "Updating and installing..."; \
    pacman -Syu --noconfirm \
        git \
        python-pytest \
        python-pytest-cov \
        python-pytest-xdist \
        python-yaml \
        python-requests \
        python-tox \
        bird \
        exabgp \
        iproute2; \
    echo "Cleaning up..."; \
    rm -f /var/cache/pacman/pkg/*
    # We don't remove sync for now as it interferes with our -Q query in runtest
    # /var/lib/pacman/sync/*

# Copy in our script
COPY runtest /root/

# Run our tests
CMD ["/root/runtest"]
