package directive

import (
	"fmt"
	"net/textproto"
	"strings"

	"github.com/kballard/go-shellquote"
	//log "github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/client"
	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/jiraplus"
	"github.com/legionus/jiramail/internal/message"
	"github.com/legionus/jiramail/internal/smtp/command"
	"github.com/legionus/jiramail/internal/smtp/command/directive/issue"
	"github.com/legionus/jiramail/internal/smtp/command/directive/sprint"
	"github.com/legionus/jiramail/internal/smtp/command/factory"
)

var (
	ErrEndOfCommands = fmt.Errorf("End of commands")
)

func init() {
	handler := &Directive{}
	factory.Register("bot@jira", handler)
	factory.Register("command@jira", handler)
}

func normalize(s string) string {
	return strings.ToLower(strings.TrimSpace(s))
}

func parseCommand(client *jiraplus.Client, msgType string, s string, hdr textproto.MIMEHeader) error {
	if len(s) == 0 || !strings.HasPrefix(s, "jira ") {
		return nil
	}

	args, err := shellquote.Split(s)
	if err != nil {
		return fmt.Errorf("unable to split string: %s", err)
	}

	if len(args) < 2 {
		return nil
	}

	args = args[1:]

	if msgType == "issue" {
		switch normalize(args[0]) {
		case "label", "labels":
			return issue.Labels(client, hdr, args[1:])
		case "watcher", "watchers":
			return issue.Watchers(client, hdr, args[1:])
		case "story":
			switch normalize(args[1]) {
			case "point", "points":
				return issue.StoryPoints(client, hdr, args[2:])
			}
		case "assignee":
			i := 1
			if normalize(args[1]) == "to" {
				i = 2
			}
			return issue.Assignee(client, hdr, args[i:])
		case "state":
			return issue.State(client, hdr, args[1:])
		case "priority":
			return issue.Priority(client, hdr, args[1:])
		default:
			return fmt.Errorf("unknown command: %s", args[0])
		}
	}

	if msgType == "sprint" {
		switch normalize(args[0]) {
		case "issue", "issues":
			return sprint.AddIssues(client, hdr, args[1:])
		default:
			return fmt.Errorf("unknown command: %s", args[0])
		}
	}

	return nil
}

var _ command.Handler = &Directive{}

type Directive struct{}

func (d *Directive) Handle(cfg *config.Configuration, msg *message.Mail) error {
	msgType := msg.Header.Get("X-Type")
	msgRemote := msg.Header.Get("X-Remote-Name")

	client, err := client.NewClient(cfg, msgRemote)
	if err != nil {
		return err
	}

	for _, line := range msg.Body {
		if err = parseCommand(client, msgType, line, msg.Header); err != nil {
			if err == ErrEndOfCommands {
				return nil
			}
			return err
		}
	}

	return nil
}
