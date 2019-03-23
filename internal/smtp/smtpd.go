package smtp

import (
	"bytes"
	"fmt"
	"net"
	"net/mail"
	"net/textproto"
	"strings"

	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/message"
	"github.com/legionus/jiramail/internal/smtp/command"
	"github.com/legionus/jiramail/internal/smtp/command/factory"
	"github.com/legionus/smtpd"

	_ "github.com/legionus/jiramail/internal/smtp/command/directive"
	_ "github.com/legionus/jiramail/internal/smtp/command/replace"
	_ "github.com/legionus/jiramail/internal/smtp/command/reply"
)

func getHandler(header textproto.MIMEHeader, key string) (command.Handler, *message.Address, error) {
	hdr := header.Get(key)
	if hdr == "" {
		return nil, nil, mail.ErrHeaderNotPresent
	}

	list, err := message.ParseAddressList(hdr)

	if err != nil {
		return nil, nil, err
	}

	for _, addr := range list {
		handler, err := factory.Get(addr.Address)
		if err != nil {
			if err != factory.InvalidMailHandlerError {
				return nil, nil, err
			}
		} else {
			return handler, addr, nil
		}
	}

	return nil, nil, factory.InvalidMailHandlerError
}

func validate(header textproto.MIMEHeader) error {
	for _, name := range []string{"Message-ID", "References", "In-Reply-To"} {
		v := header.Get(name)
		if len(v) == 0 {
			return fmt.Errorf("header %s is empty", name)
		}
	}
	return nil
}

func mailHandler(cfg *config.Configuration, remoteAddr net.Addr, from string, to []string, data []byte) {
	msg, err := message.ReadMail(cfg, bytes.NewReader(data))
	if err != nil {
		logrus.Errorf("smtp: %s", err)
		return
	}
	data = nil

	err = validate(msg.Header)
	if err != nil {
		logrus.Errorf("smtp: %s", err)
		return
	}

	for _, ref := range strings.Fields(msg.Header["References"][0]) {
		if !strings.HasSuffix(ref, ".jira>") {
			continue
		}

		err = message.DecodeMessageID(ref, msg.Header)

		if err != nil {
			logrus.Errorf("smtp: %s", err)
			return
		}
	}

	var handler command.Handler

	for _, key := range []string{"To", "Cc", "Bcc"} {
		handler, msg.Rcpt, err = getHandler(msg.Header, key)
		if err == nil {
			break
		}
		if err == factory.InvalidMailHandlerError {
			continue
		}
		logrus.Error(err)
		return
	}

	if err == factory.InvalidMailHandlerError {
		handler, err = factory.Get("reply@jira")
		if err != nil {
			logrus.Errorf("smtp: %s", err)
			return
		}
	}

	err = handler.Handle(cfg, msg)
	if err != nil {
		logrus.Errorf("smtp: unable to handle message: %s", err)
	}
}

func Server(cfg *config.Configuration) error {
	srv := &smtpd.Server{
		Addr:     cfg.SMTP.Addr,
		Hostname: cfg.SMTP.Hostname,
	}

	if len(cfg.SMTP.TLS.CertFile) > 0 && len(cfg.SMTP.TLS.KeyFile) > 0 {
		err := srv.ConfigureTLS(cfg.SMTP.TLS.CertFile, cfg.SMTP.TLS.KeyFile)
		if err != nil {
			return err
		}
	}

	if cfg.SMTP.LogMessagesOnly {
		srv.Handler = func(remoteAddr net.Addr, from string, to []string, data []byte) {
			logrus.Infof("smtp: meessage from=%q to=%q data: %s", from, to, string(data))
		}
	} else {
		srv.Handler = func(remoteAddr net.Addr, from string, to []string, data []byte) {
			mailHandler(cfg, remoteAddr, from, to, data)
		}
	}

	authEnabled := "disabled"

	if cfg.SMTP.Auth != nil {
		srv.AuthHandler = func(remoteAddr net.Addr, user []byte) ([]byte, error) {
			logrus.Debugf("smtp: auth for user %q", string(user))

			if string(user) != cfg.SMTP.Auth.Username {
				logrus.Debugf("smtp: auth user %q not found", string(user))
				return nil, fmt.Errorf("Authentication failed")
			}

			return []byte(cfg.SMTP.Auth.Password), nil
		}
		authEnabled = "enabled"
	}

	logrus.Infof("smtp: listen: %s (auth %s)", srv.Addr, authEnabled)

	return srv.ListenAndServe()
}
