package jiraconv

import (
	"fmt"
	"net/textproto"
	"strings"
	"time"

	"github.com/andygrunwald/go-jira"

	"github.com/legionus/jiramail/internal/message"
)

func BoardMessageID(data *jira.Board) string {
	boardID := map[string]string{
		"ID": fmt.Sprintf("%d", data.ID),
	}
	return message.EncodeMessageID("board.jira", boardID)
}

func (c *Converter) Board(data *jira.Board, reply string, refs []string) (*message.Mail, error) {
	if data == nil {
		return nil, fmt.Errorf("unable to convert nil to board message")
	}

	if len(reply) == 0 {
		reply = "nobody@jira"
	}

	headers := make(textproto.MIMEHeader)

	headers.Set("Message-ID", BoardMessageID(data))
	headers.Set("Reply-To", reply)
	headers.Set("Date", time.Time(time.Time{}).Format(time.RFC1123Z))
	headers.Set("From", NobodyUser.String())
	headers.Set("Subject", fmt.Sprintf("%s (%d)", data.Name, data.ID))

	if len(refs) > 0 {
		headers.Set("In-Reply-To", refs[len(refs)-1])
		headers.Set("References", strings.Join(refs, " "))
	}

	headers.Set("X-Jira-ID", fmt.Sprintf("%d", data.ID))
	headers.Set("X-Jira-Type", data.Type)

	return &message.Mail{
		Header: headers,
	}, nil
}
