package jiraconv

import (
	"fmt"
	"net/textproto"
	"sort"
	"strings"
	"time"

	"github.com/andygrunwald/go-jira"

	"github.com/legionus/jiramail/internal/message"
)

func ProjectMessageID(data *jira.Project) string {
	projectID := map[string]string{
		"ID":  data.ID,
		"Key": data.Key,
	}
	return message.EncodeMessageID("project.jira", projectID)
}

func (c *Converter) Project(data *jira.Project, refs []string) (*message.Mail, error) {
	if data == nil {
		return nil, fmt.Errorf("unable to convert nil to project message")
	}

	lead, err := c.usercache.Get(data.Lead.Name)
	if err != nil {
		return nil, err
	}

	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", ProjectMessageID(data))
	headers.Set("Reply-To", "reply@jira")
	headers.Set("Date", time.Time(time.Time{}).Format(time.RFC1123Z))
	headers.Set("From", UserFromJira(lead).String())
	headers.Set("Subject", fmt.Sprintf("[%s] %s", data.Key, data.Name))

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	msg := message.NewMail()

	if len(data.ProjectCategory.Name) > 0 {
		msg.Meta.Set("Category", message.JiraNewColumn, data.ProjectCategory.Name)
	}
	if len(data.Components) > 0 {
		s := make([]string, len(data.Components))
		for i, component := range data.Components {
			s[i] = `"` + component.Name + `"`
		}
		sort.Strings(s)
		msg.Meta.Set("Components", message.JiraNewColumn, strings.Join(s, ", "))
	}
	if len(data.IssueTypes) > 0 {
		s := make([]string, len(data.IssueTypes))
		for i, issuetype := range data.IssueTypes {
			s[i] = `"` + issuetype.Name + `"`
		}
		sort.Strings(s)
		msg.Meta.Set("Issue types", message.JiraNewColumn, strings.Join(s, ", "))
	}
	if len(data.Email) > 0 {
		msg.Meta.Set("Email", message.JiraNewColumn, data.Email)
	}
	if len(data.URL) > 0 {
		msg.Meta.Set("URL", message.JiraNewColumn, data.URL)
	}

	msg.Header = headers
	msg.Body = []string{data.Description}

	return msg, nil
}
