package syncer

import (
	"fmt"
	"net/textproto"
	"path"
	"strings"
	"time"

	"github.com/mitchellh/go-wordwrap"
	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/jiraconv"
	"github.com/legionus/jiramail/internal/maildir"
	"github.com/legionus/jiramail/internal/message"
)

func (s *JiraSyncer) globalLinkTypes(mdir maildir.Dir, refs []string) error {
	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", "issue.types@global.jira")
	headers.Set("Reply-To", "nobody@jira")
	headers.Set("Date", time.Time{}.Format(time.RFC1123Z))
	headers.Set("From", jiraconv.NobodyUser.String())
	headers.Set("Subject", "Issue types")

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	types, _, err := s.client.IssueLink.GetTypes()
	if err != nil {
		return err
	}

	body := ""
	for i, v := range types {
		body += fmt.Sprintf("%2d: %s\n", i+1, v.Name)
	}
	body += "\n"

	msg := &message.Mail{
		Header: headers,
	}

	msg.Body, err = message.BodyFromStrings(body)
	if err != nil {
		return err
	}

	return s.writeMessage(mdir, msg)
}

func (s *JiraSyncer) globalPriorities(mdir maildir.Dir, refs []string) error {
	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", "issue.priority@global.jira")
	headers.Set("Reply-To", "nobody@jira")
	headers.Set("Date", time.Time{}.Format(time.RFC1123Z))
	headers.Set("From", jiraconv.NobodyUser.String())
	headers.Set("Subject", "Issue priority")

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	priorities, _, err := s.client.Priority.GetList()
	if err != nil {
		return fmt.Errorf("unable to get priorities: %s", err)
	}

	body := ""
	for i := range priorities {
		desc := wordwrap.WrapString(strings.TrimSpace(priorities[i].Description), 80)
		body += fmt.Sprintf("### %s\n%s\n\n", priorities[i].Name, desc)
	}
	body += "\n"

	msg := &message.Mail{
		Header: headers,
	}

	msg.Body, err = message.BodyFromStrings(body)
	if err != nil {
		return err
	}

	return s.writeMessage(mdir, msg)
}

func (s *JiraSyncer) globalResolutions(mdir maildir.Dir, refs []string) error {
	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", "issue.resolution@global.jira")
	headers.Set("Reply-To", "nobody@jira")
	headers.Set("Date", time.Time{}.Format(time.RFC1123Z))
	headers.Set("From", jiraconv.NobodyUser.String())
	headers.Set("Subject", "Issue resolutions")

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	resolutions, _, err := s.client.Resolution.GetList()
	if err != nil {
		return fmt.Errorf("unable to get resolutions: %s", err)
	}

	body := ""
	for i := range resolutions {
		desc := wordwrap.WrapString(strings.TrimSpace(resolutions[i].Description), 80)
		body += fmt.Sprintf("### %s\n%s\n\n", resolutions[i].Name, desc)
	}
	body += "\n"

	msg := &message.Mail{
		Header: headers,
	}

	msg.Body, err = message.BodyFromStrings(body)
	if err != nil {
		return err
	}

	return s.writeMessage(mdir, msg)
}

func (s *JiraSyncer) Globals() error {
	logmsg := fmt.Sprintf("remote %q, globals", s.remote)
	logrus.Infof("%s begin to process", logmsg)

	mdir, err := Maildir(path.Join(s.config.Remote[s.remote].DestDir, "globals"))
	if err != nil {
		return err
	}

	refs := []string{jiraconv.RemoteMessageID(s.remote)}

	err = s.globalLinkTypes(mdir, refs)
	if err != nil {
		return err
	}

	err = s.globalPriorities(mdir, refs)
	if err != nil {
		return err
	}

	err = s.globalResolutions(mdir, refs)
	if err != nil {
		return err
	}

	logrus.Infof("%s handled", logmsg)

	return nil
}
