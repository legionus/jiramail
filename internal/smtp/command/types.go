package command

import (
	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/message"
)

type Handler interface {
	Handle(cfg *config.Configuration, msg *message.Mail) error
}

type ErrCommand struct {
	Message string
}

func (e *ErrCommand) Error() string {
	return e.Message
}

type JiraMap map[string]interface{}
