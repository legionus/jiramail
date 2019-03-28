package syncer

import (
	"io"
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

func (s *JiraSyncer) tagDeletedMessage(f *os.File) error {
	msg, err := message.ReadMail(s.config, f)
	if err != nil {
		return err
	}

	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}

	subject := msg.Header.Get("Subject")

	if strings.HasPrefix(subject, tagDeleted) {
		return nil
	}

	msg.Header["Subject"] = []string{tagDeleted + " " + subject}

	return message.Write(f, msg, s.config.Mail.JiraTableColumnWidth)
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

			err = s.tagDeletedMessage(f)
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
