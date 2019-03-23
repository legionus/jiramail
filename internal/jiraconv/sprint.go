package jiraconv

import (
	"fmt"
	"net/textproto"
	"strings"
	"time"

	"github.com/andygrunwald/go-jira"

	"github.com/legionus/jiramail/internal/message"
)

func SprintMessageID(data *jira.Sprint) string {
	sprintID := map[string]string{
		"ID": fmt.Sprintf("%d", data.ID),
	}
	return message.EncodeMessageID("sprint.jira", sprintID)
}

func (c *Converter) Sprint(data *jira.Sprint, refs []string) (*message.Mail, error) {
	if data == nil {
		return nil, fmt.Errorf("unable to convert nil to sprint message")
	}

	date := time.Time{}

	if data.StartDate != nil {
		date = *data.StartDate
	}

	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", SprintMessageID(data))
	headers.Set("Reply-To", "nobody@jira")
	headers.Set("Date", date.Format(time.RFC1123Z))
	headers.Set("From", NobodyUser.String())
	headers.Set("Subject", fmt.Sprintf("[%s] %s", strings.ToUpper(data.State), data.Name))

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	msg := message.NewMail()
	msg.Header = headers

	if data.StartDate != nil {
		msg.Meta.Set("Date start", message.JiraNewColumn, data.StartDate.Format(time.RFC1123Z))
	}
	if data.EndDate != nil {
		msg.Meta.Set("Date end", message.JiraNewColumn, data.EndDate.Format(time.RFC1123Z))
	}
	if data.CompleteDate != nil {
		msg.Meta.Set("Date complete", message.JiraNewColumn, data.CompleteDate.Format(time.RFC1123Z))
	}

	return msg, nil
}
