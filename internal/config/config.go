package config

import (
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

type LogLevel struct {
	logrus.Level
}

func (d *LogLevel) UnmarshalText(data []byte) (err error) {
	d.Level, err = logrus.ParseLevel(strings.ToLower(string(data)))
	return
}

type Configuration struct {
	Core   Core
	Mail   *Mail
	SMTP   *SMTP
	Remote map[string]*Remote
}

type Core struct {
	LogLevel   LogLevel
	LogFile    string
	LockDir    string
	SyncPeriod time.Duration
}

type Mail struct {
	MailQuote            []string
	JiraTableColumnWidth int
	Path                 *Path
}

type Path struct {
	Globals string
	Board   string
	Sprint  string
	Epic    string
	Backlog string
	Project string
}

type SMTP struct {
	Addr            string
	Hostname        string
	LockDir         string
	Auth            *SMTPAuth
	LogMessagesOnly bool
	TLS             struct {
		CertFile string
		KeyFile  string
	}
}

type SMTPAuth struct {
	Username string
	Password string
}

type Remote struct {
	DestDir      string
	BaseURL      string
	Username     string
	Password     string
	ProjectMatch string
	BoardMatch   string
	Delete       string
}
