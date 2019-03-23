package syncer

import (
	"io/ioutil"
	"net/mail"
	"net/textproto"
	"os"
	"strings"

	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/maildir"
	"github.com/legionus/jiramail/internal/message"
)

const (
	tagDeleted = "[DELETED]"
)

func tagDeletedMessage(f *os.File) error {
	m, err := mail.ReadMessage(f)
	if err != nil {
		return err
	}

	subject := m.Header.Get("Subject")

	if strings.HasPrefix(subject, tagDeleted) {
		return nil
	}

	b, err := ioutil.ReadAll(m.Body)
	if err != nil {
		return err
	}

	msg := &message.Mail{
		Header: textproto.MIMEHeader(m.Header),
	}

	msg.Body, err = message.BodyFromBytes(b)
	if err != nil {
		return err
	}

	msg.Header["Subject"] = []string{tagDeleted + " " + subject}

	return message.Write(f, msg)
}

func (s *JiraSyncer) CleanDir(mdir maildir.Dir) error {
	msgids, err := mdir.Keys()
	if err != nil {
		return err
	}

	for _, msgid := range msgids {
		if _, ok := s.msgids[msgid]; ok {
			continue
		}

		headers := make(textproto.MIMEHeader)

		err = message.DecodeMessageID(msgid, headers)
		if err != nil {
			logrus.Warnf("unable to decode MessageID %q: %s", msgid, err)
		}

		if s.config.Remote[s.remote].Delete == "tag" {
			fn, err := mdir.Filename(msgid)
			if err != nil {
				return err
			}
			f, err := os.OpenFile(fn, os.O_RDWR, 0644)
			if err != nil {
				return err
			}

			err = tagDeletedMessage(f)
			f.Close()

			if err != nil {
				return err
			}
		} else {
			err = mdir.Purge(msgid)
			if err != nil {
				return err
			}
		}
	}

	err = mdir.Clean()
	if err != nil {
		return err
	}
	return nil
}
