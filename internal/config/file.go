package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gopkg.in/yaml.v2"
)

func substHome(s string) string {
	arr := strings.Split(s, string(os.PathSeparator))
	if arr[0] == "~" {
		arr[0] = os.Getenv("HOME")
		return filepath.Join(arr...)
	}
	return s
}

func Read(filename string) (*Configuration, error) {
	cfg := &Configuration{}

	cfg.Core.SyncPeriod = 5 * time.Minute

	f, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	err = yaml.NewDecoder(f).Decode(cfg)
	if err != nil {
		return nil, err
	}

	cfg.Core.LogFile = substHome(cfg.Core.LogFile)
	cfg.Core.LockDir = substHome(cfg.Core.LockDir)
	cfg.SMTP.LockDir = substHome(cfg.SMTP.LockDir)
	cfg.SMTP.TLS.CertFile = substHome(cfg.SMTP.TLS.CertFile)
	cfg.SMTP.TLS.KeyFile = substHome(cfg.SMTP.TLS.KeyFile)

	if (len(cfg.SMTP.TLS.CertFile) == 0 && len(cfg.SMTP.TLS.KeyFile) > 0) ||
		(len(cfg.SMTP.TLS.CertFile) > 0 && len(cfg.SMTP.TLS.KeyFile) == 0) {
		return nil, fmt.Errorf("you must specify CertFile and KeyFile to enable TLS")
	}

	for name := range cfg.Remote {
		cfg.Remote[name].DestDir = substHome(cfg.Remote[name].DestDir)

		cfg.Remote[name].Delete = strings.ToLower(cfg.Remote[name].Delete)

		switch cfg.Remote[name].Delete {
		case "remove", "tag":
		case "":
			cfg.Remote[name].Delete = "remove"
		default:
			return nil, fmt.Errorf("unknown value %q, expected 'remove' or 'tag'", cfg.Remote[name].Delete)
		}
	}

	return cfg, nil
}
