package reply

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/andygrunwald/go-jira"
	//log "github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/client"
	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/message"
	"github.com/legionus/jiramail/internal/smtp/command"
	"github.com/legionus/jiramail/internal/smtp/command/factory"
)

var _ command.Handler = &Reply{}

func init() {
	factory.Register("reply@jira", &Reply{})
}

type Reply struct{}

func (r *Reply) Handle(cfg *config.Configuration, msg *message.Mail) error {
	msgType := msg.Header.Get("X-Type")

	switch msgType {
	case "issue":
		if _, ok := msg.Rcpt.Tags["subtask"]; ok {
			return addIssue(cfg, msg, true)
		}
		return addComment(cfg, msg)
	case "comment":
		return addComment(cfg, msg)
	case "project":
		return addIssue(cfg, msg, false)
	case "board":
		if _, ok := msg.Rcpt.Tags["sprint"]; ok {
			return fmt.Errorf("not implemented: %s+sprint", msgType)
		}
		if _, ok := msg.Rcpt.Tags["epic"]; ok {
			return fmt.Errorf("not implemented: %s+epic", msgType)
		}
	}

	return fmt.Errorf("unsupported message type: %s", msgType)
}

func addComment(cfg *config.Configuration, msg *message.Mail) error {
	client, err := client.NewClient(cfg, msg.Header.Get("X-Remote-Name"))
	if err != nil {
		return err
	}

	msgID := msg.Header.Get("X-Issue-Key")

	_, _, err = client.PlusIssue.AddComment(msgID, &jira.Comment{Body: msg.GetBody()})
	if err != nil {
		return fmt.Errorf("unable to add comment to %s issue: %s", msgID, err)
	}

	return nil
}

func getIssueType(s string, project *jira.Project, subtask bool) (string, string, error) {
	if len(project.IssueTypes) == 0 {
		return "", "", fmt.Errorf("issue types do not exist")
	}

	res := regexp.MustCompile(`(?i:\[(?:\?|JIRA)\s*TYPE\s+([^\]]+)\])`).FindStringSubmatch(s)
	if len(res) == 0 {
		if subtask {
			for i, v := range project.IssueTypes {
				if v.Subtask {
					return project.IssueTypes[i].Name, s, nil
				}
			}
		}
		return project.IssueTypes[0].Name, s, nil
	}

	for _, v := range project.IssueTypes {
		if subtask && !v.Subtask {
			continue
		}
		if strings.EqualFold(res[1], v.Name) {
			s = strings.Replace(s, res[0], "", -1)
			return v.Name, s, nil
		}
	}

	return "", "", fmt.Errorf("issue type %s not found", res[1])
}

func addIssue(cfg *config.Configuration, msg *message.Mail, subtask bool) error {
	client, err := client.NewClient(cfg, msg.Header.Get("X-Remote-Name"))
	if err != nil {
		return err
	}

	project, _, err := client.Project.Get(msg.Header.Get("X-Project-Id"))
	if err != nil {
		return fmt.Errorf("unable to get project %s: %s", msg.Header.Get("X-Project-Key"), err)
	}

	issueType, subject, err := getIssueType(msg.Header.Get("Subject"), project, subtask)
	if err != nil {
		return err
	}

	issue := jira.Issue{
		Fields: &jira.IssueFields{
			Project: *project,
			Type: jira.IssueType{
				Name: issueType,
			},
			Summary:     subject,
			Description: msg.GetBody(),
		},
	}

	if subtask {
		issue.Fields.Type.Subtask = true
		issue.Fields.Parent = &jira.Parent{
			ID:  msg.Header.Get("X-Issue-Id"),
			Key: msg.Header.Get("X-Issue-Key"),
		}
	}

	_, _, err = client.PlusIssue.Create(&issue)
	if err != nil {
		return fmt.Errorf("unable to add issue: %s", err)
	}

	return nil
}
