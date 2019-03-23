package jiraconv

import (
	"fmt"
	"net/textproto"
	"strings"
	"time"

	"github.com/andygrunwald/go-jira"

	"github.com/legionus/jiramail/internal/message"
)

func EpicMessageID(data *jira.Epic) string {
	epicID := map[string]string{
		"ID":  fmt.Sprintf("%d", data.ID),
		"Key": data.Key,
	}
	return message.EncodeMessageID("epic.jira", epicID)
}

func (c *Converter) Epic(data *jira.Epic, refs []string) (*message.Mail, error) {
	if data == nil {
		return nil, fmt.Errorf("unable to convert nil to epic message")
	}

	doneTag := ""
	if data.Done {
		doneTag = "[DONE]"
	}

	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", EpicMessageID(data))
	headers.Set("Reply-To", "nobody@jira")
	headers.Set("Date", time.Time{}.Format(time.RFC1123Z))
	headers.Set("From", NobodyUser.String())
	headers.Set("Subject", fmt.Sprintf("[%s]%s %s", data.Key, doneTag, data.Name))

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	return &message.Mail{
		Header: headers,
		Body:   []string{data.Summary},
	}, nil
}
