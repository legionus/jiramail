package syncer

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/cache"
	"github.com/legionus/jiramail/internal/client"
	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/jiraconv"
	"github.com/legionus/jiramail/internal/jiraplus"
	"github.com/legionus/jiramail/internal/maildir"
	"github.com/legionus/jiramail/internal/message"
)

type JiraSyncer struct {
	client    *jiraplus.Client
	converter *jiraconv.Converter
	config    *config.Configuration
	remote    string
	msgids    map[string]struct{}
	projects  map[string]struct{}
}

func NewJiraSyncer(c *config.Configuration, remoteName string) (*JiraSyncer, error) {
	jiraClient, err := client.NewClient(c, remoteName)
	if err != nil {
		return nil, err
	}

	s := &JiraSyncer{
		config:    c,
		remote:    remoteName,
		client:    jiraClient,
		converter: jiraconv.NewConverter(remoteName, cache.NewUserCache(jiraClient)),
		msgids:    make(map[string]struct{}),
		projects:  make(map[string]struct{}),
	}

	fields, _, err := jiraClient.Field.GetList()
	if err != nil {
		return nil, err
	}

	s.converter.SetJiraFields(fields)

	return s, nil
}

func SyncAll(c *config.Configuration) error {
	for name := range c.Remote {
		jiraSyncer, err := NewJiraSyncer(c, name)
		if err != nil {
			return err
		}

		err = jiraSyncer.Globals()
		if err != nil {
			return err
		}

		err = jiraSyncer.Boards()
		if err != nil {
			return err
		}

		err = jiraSyncer.Projects()
		if err != nil {
			return err
		}

	}

	logrus.Infof("synchronization is completed")
	return nil
}

func (s *JiraSyncer) readMessage(mdir maildir.Dir, msg *message.Mail) (*message.Mail, error) {
	messageID := msg.HeaderID()

	fp, err := mdir.Filename(messageID)

	if err != nil {
		mailErr, ok := err.(*maildir.KeyError)
		if ok && mailErr.N == 0 {
			return nil, nil
		}
		return nil, err
	}

	nmsg, err := message.ReadMailfile(s.config, fp)
	if err != nil {
		return nil, err
	}

	return nmsg, nil
}

func (s *JiraSyncer) writeMessage(mdir maildir.Dir, msg *message.Mail) error {
	messageID := msg.HeaderID()

	curMessageHash, err := getMessageHash(s.config, mdir, messageID)
	if err != nil {
		return err
	}

	newMessageHash, err := message.MakeChecksum(msg)
	if err != nil {
		return err
	}

	if curMessageHash == newMessageHash {
		s.msgids[messageID] = struct{}{}
		return nil
	}

	d, err := mdir.NewDeliveryKey(messageID)
	if err != nil {
		return fmt.Errorf("can not create ongoing message delivery to the mailbox: %s", err)
	}

	msg.Header["X-Checksum"] = []string{newMessageHash}

	err = message.Write(d, msg)
	if err != nil {
		d.Abort()
		return err
	}

	if err = CloseDelivery(mdir, messageID, d); err != nil {
		return err
	}

	s.msgids[messageID] = struct{}{}
	return nil
}

func CloseDelivery(mdir maildir.Dir, key string, d *maildir.Delivery) error {
	flags, err := mdir.Flags(key)
	if err != nil {
		mailErr, ok := err.(*maildir.KeyError)
		if ok && mailErr.N != 0 {
			return err
		}
		flags = ""
	} else {
		flags = strings.Replace(flags, "S", "", -1)
	}

	err = mdir.Purge(key)
	if err != nil {
		mailErr, ok := err.(*maildir.KeyError)
		if ok && mailErr.N != 0 {
			return err
		}
	}

	err = d.Close()
	if err != nil {
		return err
	}

	return nil
}

func getMessageHash(cfg *config.Configuration, mdir maildir.Dir, key string) (string, error) {
	fp, err := mdir.Filename(key)

	if err != nil {
		mailErr, ok := err.(*maildir.KeyError)
		if ok && mailErr.N == 0 {
			return "", nil
		}
		return "", err
	}

	return message.GetChecksum(cfg, fp)
}

func Maildir(p string) (maildir.Dir, error) {
	st, err := os.Stat(p)
	if err != nil {
		if !os.IsNotExist(err) {
			return "", err
		}
		err := os.MkdirAll(filepath.Dir(p), 0755)
		if err != nil {
			return "", err
		}
		if err := maildir.Dir(p).Create(); err != nil {
			return "", fmt.Errorf("unable to create maildir: %s", err)
		}
	} else {
		if !st.Mode().IsDir() {
			return "", fmt.Errorf("dirctory expected: %s", p)
		}
	}
	return maildir.Dir(p), nil
}
