# Security

- Change the example emergency PIN before deployment.
- Change the example package-locker operator PIN before deployment. Use a
  different PIN from the emergency PIN.
- Keep `config.yaml`, `.env`, Home Assistant tokens, and notification-provider
  credentials out of Git.
- Keep Nova on the trusted home network; do not expose port 8787 directly to the
  public internet.
- Put authenticated HTTPS in front of Nova before allowing remote caregiver
  access.
- Never expose locker endpoints directly to the internet.
- Use an opto-isolated relay or dedicated lock controller; do not power a
  solenoid lock from the Raspberry Pi GPIO pin.
- Test relay polarity in simulation and with the lock disconnected. Hardware
  and software must both fail to the locked state.
- Generated package codes are one-time credentials. Send them only to the
  intended courier and use short expirations.
- Test SOS notifications with trusted contacts before enabling outbound alerts.
- Nova is a household support tool, not a medical device or guaranteed emergency
  dispatch service.
